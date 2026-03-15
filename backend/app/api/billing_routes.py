"""Billing/plan management routes — plan comparison, Stripe checkout, subscription."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.deps import CurrentUser
from app.config import settings
from app.models.plan import Plan, PlanCode, UserSubscription
from app.api.schemas import PlanResponse, ChangePlanRequest

logger = logging.getLogger(__name__)

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
    If Stripe is configured and plan is paid, creates a Stripe Checkout session.
    Otherwise, directly swaps the plan (for free tier or dev mode).
    """
    result = await db.execute(select(Plan).where(Plan.code == body.plan_code))
    new_plan = result.scalar_one_or_none()
    if not new_plan:
        raise HTTPException(status_code=400, detail="Invalid plan code")

    # If downgrading to free or Stripe not configured, do direct swap
    if new_plan.price_monthly_cents == 0 or not settings.STRIPE_SECRET_KEY:
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan_id = new_plan.id
            sub.status = "active"
            sub.stripe_subscription_id = None
        else:
            sub = UserSubscription(user_id=user.id, plan_id=new_plan.id, status="active")
            db.add(sub)
        await db.flush()
        return {
            "ok": True,
            "plan": {"name": new_plan.name, "code": new_plan.code},
            "message": f"Switched to {new_plan.name} plan.",
        }

    # Stripe Checkout for paid plans
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Determine Stripe price ID
        price_id = None
        if new_plan.code == PlanCode.PRO.value:
            price_id = settings.STRIPE_PRICE_ID_PRO or new_plan.stripe_price_id
        elif new_plan.code == PlanCode.MAX.value:
            price_id = settings.STRIPE_PRICE_ID_MAX or new_plan.stripe_price_id

        if not price_id:
            # Fallback: direct swap if no Stripe price configured
            result = await db.execute(
                select(UserSubscription).where(UserSubscription.user_id == user.id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.plan_id = new_plan.id
                sub.status = "active"
            else:
                sub = UserSubscription(user_id=user.id, plan_id=new_plan.id, status="active")
                db.add(sub)
            await db.flush()
            return {
                "ok": True,
                "plan": {"name": new_plan.name, "code": new_plan.code},
                "message": f"Switched to {new_plan.name} plan (Stripe price not configured).",
            }

        checkout_session = stripe.checkout.Session.create(
            customer_email=user.email,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/dashboard/pricing?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/pricing?canceled=true",
            metadata={"plan_code": new_plan.code, "user_id": str(user.id)},
        )

        return {
            "ok": True,
            "checkout_url": checkout_session.url,
            "message": "Redirecting to Stripe Checkout...",
        }
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        # Fallback: direct swap
        result = await db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user.id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan_id = new_plan.id
            sub.status = "active"
        else:
            sub = UserSubscription(user_id=user.id, plan_id=new_plan.id, status="active")
            db.add(sub)
        await db.flush()
        return {
            "ok": True,
            "plan": {"name": new_plan.name, "code": new_plan.code},
            "message": f"Switched to {new_plan.name} plan.",
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
        return {"plan": "Free", "code": "plan_free", "status": "active", "price_monthly_cents": 0}

    return {
        "plan": sub.plan.name,
        "code": sub.plan.code,
        "status": sub.status,
        "price_monthly_cents": sub.plan.price_monthly_cents,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "stripe_subscription_id": sub.stripe_subscription_id,
    }


@router.post("/portal")
async def create_portal_session(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active Stripe subscription")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Get customer from subscription
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
        portal = stripe.billing_portal.Session.create(
            customer=stripe_sub.customer,
            return_url=f"{settings.FRONTEND_URL}/dashboard/pricing",
        )
        return {"url": portal.url}
    except Exception as e:
        logger.error(f"Stripe portal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create billing portal")
