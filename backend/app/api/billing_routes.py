"""Billing/plan management routes — plan comparison, change plan, usage."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.plan import Plan, PlanCode, UserSubscription
from app.api.schemas import PlanResponse, ChangePlanRequest

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all available plans for the pricing page."""
    result = await db.execute(select(Plan).order_by(Plan.price_monthly_cents))
    plans = result.scalars().all()
    return [PlanResponse(
        name=p.name, code=p.code, monthly_request_limit=p.monthly_request_limit,
        max_projects=p.max_projects, max_features_per_project=p.max_features_per_project,
        auto_mode_enabled=p.auto_mode_enabled, price_monthly_cents=p.price_monthly_cents,
    ) for p in plans]


@router.post("/change-plan")
async def change_plan(body: ChangePlanRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Change the user's subscription plan.
    In production, this would integrate with Stripe Checkout.
    For MVP, we directly swap the plan.
    """
    # Validate plan code
    result = await db.execute(select(Plan).where(Plan.code == body.plan_code))
    new_plan = result.scalar_one_or_none()
    if not new_plan:
        raise HTTPException(status_code=400, detail="Invalid plan code")

    # Get or create subscription
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.plan_id = new_plan.id
        sub.status = "active"
        # In production: sub.stripe_subscription_id = stripe_sub.id
    else:
        sub = UserSubscription(user_id=user.id, plan_id=new_plan.id, status="active")
        db.add(sub)

    await db.flush()

    return {
        "ok": True,
        "plan": {"name": new_plan.name, "code": new_plan.code},
        "message": f"Switched to {new_plan.name} plan.",
        # In production: "checkout_url": stripe_checkout_session.url
    }


@router.get("/subscription")
async def get_subscription(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Return current subscription details."""
    result = await db.execute(
        select(UserSubscription)
        .options(selectinload(UserSubscription.plan))
        .where(UserSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return {"plan": "Free", "status": "active"}

    return {
        "plan": sub.plan.name,
        "code": sub.plan.code,
        "status": sub.status,
        "price_monthly_cents": sub.plan.price_monthly_cents,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "stripe_subscription_id": sub.stripe_subscription_id,
    }
