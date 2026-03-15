"""Feature and feature-level settings models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("project_id", "slug", name="uq_project_feature_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="features")
    settings: Mapped["FeatureSetting"] = relationship(back_populates="feature", uselist=False, cascade="all, delete-orphan")
    daily_stats: Mapped[list["FeatureStatsDaily"]] = relationship(back_populates="feature", cascade="all, delete-orphan")


class FeatureSetting(Base):
    __tablename__ = "feature_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    auto_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    max_tokens_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    preferred_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    monthly_budget_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    feature: Mapped["Feature"] = relationship(back_populates="settings")
