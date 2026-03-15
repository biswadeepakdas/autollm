"""Admin routes — internal/admin endpoints for managing the platform."""

import logging
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.user import User
from app.models.plan import Plan, UserSubscription
from app.models.project import Project
from app.models.stats import FeatureStatsDaily

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_admin(user: User) -> None:
    """Raise 403 if the user is not an admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


# ── Response schemas ─────────────────────────────────────────────────────────

class AdminStatsResponse(BaseModel):
    users: int
    total_requests: int
    total_cost_cents: float
    projects: int
    plan_distribution: dict[str, int]


class AdminUserItem(BaseModel):
    id: str
    email: str
    name: str | None
    plan: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUsersResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
    page: int
    per_page: int
    pages: int


# ── GET /api/admin/stats ─────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Return high-level platform stats (admin only)."""
    _require_admin(user)

    # Total users
    result = await db.execute(select(func.count(User.id)))
    user_count = result.scalar() or 0

    # Total projects
    result = await db.execute(select(func.count(Project.id)))
    project_count = result.scalar() or 0

    # Total requests and cost from daily stats
    result = await db.execute(
        select(
            func.coalesce(func.sum(FeatureStatsDaily.total_requests), 0),
            func.coalesce(func.sum(FeatureStatsDaily.total_cost_cents), 0.0),
        )
    )
    row = result.one()
    total_requests = int(row[0])
    total_cost_cents = float(row[1])

    # Plan distribution: plan_name -> count of active subscriptions
    result = await db.execute(
        select(Plan.name, func.count(UserSubscription.id))
        .join(UserSubscription, UserSubscription.plan_id == Plan.id)
        .where(UserSubscription.status == "active")
        .group_by(Plan.name)
    )
    plan_distribution = {name: count for name, count in result.all()}

    return AdminStatsResponse(
        users=user_count,
        total_requests=total_requests,
        total_cost_cents=total_cost_cents,
        projects=project_count,
        plan_distribution=plan_distribution,
    )


# ── GET /api/admin/users ─────────────────────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
async def admin_users(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Return paginated user list (admin only)."""
    _require_admin(user)

    # Total count
    result = await db.execute(select(func.count(User.id)))
    total = result.scalar() or 0
    pages = max(1, math.ceil(total / per_page))

    # Fetch users with their subscriptions (and plans)
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription).selectinload(UserSubscription.plan))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    db_users = result.scalars().all()

    items = []
    for u in db_users:
        plan_name = "Free"
        if u.subscription and u.subscription.plan:
            plan_name = u.subscription.plan.name
        items.append(AdminUserItem(
            id=str(u.id),
            email=u.email,
            name=u.name,
            plan=plan_name,
            is_admin=u.is_admin,
            created_at=u.created_at,
        ))

    return AdminUsersResponse(
        users=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ── PATCH /api/admin/users/{user_id}/plan ────────────────────────────────────

@router.patch("/users/{user_id}/plan")
async def change_user_plan(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    plan_code: str = Query(...),
):
    """Change a user's subscription plan (admin only)."""
    _require_admin(user)

    # Find target user
    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the plan
    result = await db.execute(select(Plan).where(Plan.code == plan_code))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan code: {plan_code}")

    if target_user.subscription:
        target_user.subscription.plan_id = plan.id
    else:
        sub = UserSubscription(user_id=target_user.id, plan_id=plan.id, status="active")
        db.add(sub)

    await db.flush()
    return {"ok": True, "plan": plan.name}


# ── PATCH /api/admin/users/{user_id}/admin ───────────────────────────────────

@router.patch("/users/{user_id}/admin")
async def toggle_admin(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Toggle admin status for a user (admin only)."""
    _require_admin(user)

    # Prevent removing your own admin status
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin status")

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_admin = not target_user.is_admin
    await db.flush()

    return {"ok": True, "is_admin": target_user.is_admin}
