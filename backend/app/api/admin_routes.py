"""Admin routes — internal/admin endpoints for managing the platform."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.user import User
from app.models.plan import UserSubscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Return high-level platform stats (admin only)."""
    if not user.email.endswith("@autollm.com"):
        raise HTTPException(status_code=403, detail="Admin access required")

    user_count = await db.execute(select(func.count(User.id)))
    sub_count = await db.execute(select(func.count(UserSubscription.id)))

    return {
        "total_users": user_count.scalar() or 0,
        "total_subscriptions": sub_count.scalar() or 0,
    }
