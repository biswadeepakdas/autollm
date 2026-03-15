"""Auto mode suggestion model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class SuggestionType(str, enum.Enum):
    MODEL_DOWNGRADE = "model_downgrade"          # Rule 1: cheaper model for small prompts
    TOKEN_CAP = "token_cap"                      # Rule 2: enforce max_tokens
    LOW_VALUE_CUT = "low_value_cut"              # Rule 3: low-value, high-cost feature
    PROVIDER_MIX = "provider_mix"                # Rule 4: cheaper provider alternative
    BUDGET_ALERT = "budget_alert"                # Rule 5: spending alert


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    AUTO_APPLIED = "auto_applied"


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("features.id", ondelete="SET NULL"), nullable=True)

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_savings_cents: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0–1

    # What the suggestion recommends
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=SuggestionStatus.PENDING.value)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # higher = more important

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
