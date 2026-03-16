"""Webhook routes — Stripe webhook handling."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException

from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

# ── In-memory idempotency set ────────────────────────────────────────────────
# Keeps track of already-processed Stripe event IDs so we never handle the
# same event twice (Stripe may retry delivery).  For a single-process deploy
# this is sufficient; for multi-process / multi-instance deployments swap this
# for a Redis set or a DB table.
_processed_event_ids: set[str] = set()
_MAX_PROCESSED_IDS = 10_000  # cap to avoid unbounded memory growth


def _record_event(event_id: str) -> bool:
    """Return True if the event is new (not yet processed).
    Return False if it was already seen (duplicate)."""
    if event_id in _processed_event_ids:
        return False
    # Evict oldest entries when the set grows too large.  Since Python 3.7+
    # sets don't guarantee insertion order we just clear the whole set; this
    # is fine because duplicates within a short window are what matter most.
    if len(_processed_event_ids) >= _MAX_PROCESSED_IDS:
        _processed_event_ids.clear()
    _processed_event_ids.add(event_id)
    return True


def _get_event_field(event, field: str):
    """Safely read a field from either a dict-based or Stripe object event."""
    if isinstance(event, dict):
        return event.get(field)
    return getattr(event, field, None)


def _get_data_object(event) -> dict:
    """Extract the nested data.object regardless of event format."""
    if isinstance(event, dict):
        return event.get("data", {}).get("object", {})
    return event.data.object


# ── Price ID -> plan code mapping ────────────────────────────────────────────

def _build_price_to_plan_map() -> dict[str, str]:
    """Build a mapping of Stripe price IDs to plan codes from settings."""
    from app.config import settings
    from app.models.plan import PlanCode

    mapping: dict[str, str] = {}
    if settings.STRIPE_PRICE_ID_PRO:
        mapping[settings.STRIPE_PRICE_ID_PRO] = PlanCode.PRO.value
    if settings.STRIPE_PRICE_ID_MAX:
        mapping[settings.STRIPE_PRICE_ID_MAX] = PlanCode.MAX.value
    return mapping


# ── Webhook endpoint ─────────────────────────────────────────────────────────

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

        event_id = _get_event_field(event, "id")
        event_type = _get_event_field(event, "type")

        logger.info("stripe_webhook_received", event_type=event_type, event_id=event_id)

        # ── Idempotency check ────────────────────────────────────────────
        if event_id and not _record_event(event_id):
            logger.info("stripe_webhook_duplicate", event_id=event_id)
            return {"status": "ok", "detail": "duplicate event ignored"}

        # ── Route to handler ─────────────────────────────────────────────
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(event)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(event)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(event)
        else:
            logger.debug("stripe_webhook_unhandled", event_type=event_type)

        return {"status": "ok"}

    except stripe.error.SignatureVerificationError as e:
        logger.error("stripe_signature_invalid", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("stripe_webhook_error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# ── Event handlers ───────────────────────────────────────────────────────────

async def _handle_checkout_completed(event):
    """Handle successful checkout — activate the user's subscription."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, UserSubscription

    data = _get_data_object(event)
    metadata = data.get("metadata", {})
    plan_code = metadata.get("plan_code")
    user_id = metadata.get("user_id")
    stripe_sub_id = data.get("subscription")

    if not plan_code or not user_id:
        logger.warning("checkout_missing_metadata")
        return

    import uuid
    async with async_session() as session:
        result = await session.execute(select(Plan).where(Plan.code == plan_code))
        plan = result.scalar_one_or_none()
        if not plan:
            logger.error("plan_not_found", plan_code=plan_code)
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
        logger.info("subscription_activated", user_id=user_id, plan_code=plan_code)


async def _handle_subscription_updated(event):
    """Handle subscription changes — update the user's plan and status.

    Stripe fires this event whenever a subscription's status or items change
    (upgrade, downgrade, renewal, going past_due, etc.).
    """
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, UserSubscription, PlanCode

    data = _get_data_object(event)
    stripe_sub_id = data.get("id")
    stripe_status = data.get("status")  # active, past_due, canceled, etc.

    if not stripe_sub_id:
        logger.warning("subscription_updated_missing_id")
        return

    # Determine the new price ID from the subscription items
    items = data.get("items", {}).get("data", [])
    new_price_id = items[0].get("price", {}).get("id") if items else None

    price_to_plan = _build_price_to_plan_map()
    new_plan_code = price_to_plan.get(new_price_id) if new_price_id else None

    # Map Stripe status -> our SubscriptionStatus values
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "trialing": "trialing",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
        "unpaid": "past_due",
    }
    mapped_status = status_map.get(stripe_status, "active")

    async with async_session() as session:
        result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            logger.warning("subscription_not_found", stripe_sub_id=stripe_sub_id)
            return

        # Update status
        sub.status = mapped_status

        # Update plan if we can resolve the price ID
        if new_plan_code:
            plan_result = await session.execute(
                select(Plan).where(Plan.code == new_plan_code)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                sub.plan_id = plan.id
                logger.info("subscription_plan_changed", stripe_sub_id=stripe_sub_id, new_plan=new_plan_code)
            else:
                logger.warning("plan_not_found", plan_code=new_plan_code)
        elif new_price_id:
            # Price ID not in our config — try matching via Plan.stripe_price_id
            plan_result = await session.execute(
                select(Plan).where(Plan.stripe_price_id == new_price_id)
            )
            plan = plan_result.scalar_one_or_none()
            if plan:
                sub.plan_id = plan.id
                logger.info("subscription_plan_changed", stripe_sub_id=stripe_sub_id, new_plan=plan.code, matched_via="stripe_price_id")

        # Update period timestamps if present
        period_start = data.get("current_period_start")
        period_end = data.get("current_period_end")
        if period_start:
            sub.current_period_start = datetime.fromtimestamp(period_start, tz=timezone.utc)
        if period_end:
            sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

        await session.commit()
        logger.info("subscription_updated", stripe_sub_id=stripe_sub_id, status=mapped_status)


async def _handle_subscription_deleted(event):
    """Handle subscription cancellation — downgrade the user to the free plan."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, UserSubscription, PlanCode

    data = _get_data_object(event)
    stripe_sub_id = data.get("id")

    if not stripe_sub_id:
        logger.warning("subscription_deleted_missing_id")
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            logger.warning("subscription_not_found", stripe_sub_id=stripe_sub_id)
            return

        # Look up the free plan
        plan_result = await session.execute(
            select(Plan).where(Plan.code == PlanCode.FREE.value)
        )
        free_plan = plan_result.scalar_one_or_none()
        if not free_plan:
            logger.error("free_plan_not_found")
            return

        sub.plan_id = free_plan.id
        sub.status = "canceled"
        sub.stripe_subscription_id = None  # clear the Stripe reference

        await session.commit()
        logger.info("subscription_deleted", stripe_sub_id=stripe_sub_id, user_id=str(sub.user_id))


async def _handle_payment_failed(event):
    """Handle a failed invoice payment.

    Strategy:
    - Log a warning with relevant details.
    - If the related subscription is already past_due (Stripe sets this
      automatically after repeated failures), downgrade the user to the
      free plan as a grace-period expiry measure.
    - Otherwise, leave the subscription in its current state; Stripe will
      retry the payment according to its Smart Retries / dunning settings.
    """
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, UserSubscription, PlanCode

    data = _get_data_object(event)
    stripe_sub_id = data.get("subscription")
    customer_email = data.get("customer_email")
    attempt_count = data.get("attempt_count", 0)

    logger.warning("payment_failed", stripe_sub_id=stripe_sub_id, customer_email=customer_email, attempt_count=attempt_count)

    if not stripe_sub_id:
        return

    async with async_session() as session:
        result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            logger.warning("subscription_not_found", stripe_sub_id=stripe_sub_id, context="payment_failed_downgrade")
            return

        # Downgrade to free after 3+ failed attempts (grace period expired)
        if attempt_count >= 3:
            plan_result = await session.execute(
                select(Plan).where(Plan.code == PlanCode.FREE.value)
            )
            free_plan = plan_result.scalar_one_or_none()
            if free_plan:
                sub.plan_id = free_plan.id
                sub.status = "past_due"
                await session.commit()
                logger.warning("grace_period_expired", stripe_sub_id=stripe_sub_id, user_id=str(sub.user_id))
            else:
                logger.error("free_plan_not_found", context="payment_failure_downgrade")
        else:
            # Mark as past_due but keep current plan
            sub.status = "past_due"
            await session.commit()
            logger.info("subscription_past_due", stripe_sub_id=stripe_sub_id, attempt_count=attempt_count)
