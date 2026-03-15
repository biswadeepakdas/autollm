"""Webhook routes — Stripe webhook handling."""

import logging

from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (subscription updates, payment failures, etc.)."""
    from app.config import settings

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if settings.STRIPE_WEBHOOK_SECRET and sig_header:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        else:
            import json
            event = json.loads(payload)

        event_type = event.get("type") if isinstance(event, dict) else event.type

        logger.info(f"Stripe webhook received: {event_type}")

        # Handle specific events
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event)
        elif event_type == "customer.subscription.updated":
            logger.info("Subscription updated event received")
        elif event_type == "customer.subscription.deleted":
            logger.info("Subscription deleted event received")
        elif event_type == "invoice.payment_failed":
            logger.warning("Payment failed event received")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def _handle_checkout_completed(event):
    """Handle successful checkout — activate the user's subscription."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, UserSubscription

    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
    metadata = data.get("metadata", {})
    plan_code = metadata.get("plan_code")
    user_id = metadata.get("user_id")
    stripe_sub_id = data.get("subscription")

    if not plan_code or not user_id:
        logger.warning("Checkout session missing metadata")
        return

    import uuid
    async with async_session() as session:
        result = await session.execute(select(Plan).where(Plan.code == plan_code))
        plan = result.scalar_one_or_none()
        if not plan:
            logger.error(f"Plan not found: {plan_code}")
            return

        result = await session.execute(
            select(UserSubscription).where(UserSubscription.user_id == uuid.UUID(user_id))
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan_id = plan.id
            sub.status = "active"
            sub.stripe_subscription_id = stripe_sub_id
        else:
            sub = UserSubscription(
                user_id=uuid.UUID(user_id),
                plan_id=plan.id,
                status="active",
                stripe_subscription_id=stripe_sub_id,
            )
            session.add(sub)

        await session.commit()
        logger.info(f"Subscription activated for user {user_id} on plan {plan_code}")
