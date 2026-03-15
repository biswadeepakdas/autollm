"""Subscription plan and user subscription models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class PlanCode(str, enum.Enum):
    FREE = "plan_free"
    PRO = "plan_pro"
    MAX = "plan_max"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # "Free", "Pro", "Max"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # plan_free, plan_pro, plan_max
    monthly_request_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    max_features_per_project: Mapped[int] = mapped_column(Integer, nullable=False)
    auto_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    price_monthly_cents: Mapped[int] = mapped_column(Integer, default=0)  # price in cents
    stripe_price_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    subscriptions: Mapped[list["UserSubscription"]] = relationship(back_populates="plan")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=SubscriptionStatus.ACTIVE.value)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions", lazy="selectin")


# ── Default plan definitions (used for seeding) ─────────────────────────────
PLAN_DEFAULTS = [
    {
        "name": "Free",
        "code": PlanCode.FREE.value,
        "monthly_request_limit": 5_000,
        "max_projects": 1,
        "max_features_per_project": 5,
        "auto_mode_enabled": False,
        "price_monthly_cents": 0,
    },
    {
        "name": "Pro",
        "code": PlanCode.PRO.value,
        "monthly_request_limit": 100_000,
        "max_projects": 5,
        "max_features_per_project": 50,
        "auto_mode_enabled": True,
        "price_monthly_cents": 4900,  # $49/mo
    },
    {
        "name": "Max",
        "code": PlanCode.MAX.value,
        "monthly_request_limit": 1_000_000,
        "max_projects": 20,
        "max_features_per_project": 200,
        "auto_mode_enabled": True,
        "price_monthly_cents": 14900,  # $149/mo
    },
]
