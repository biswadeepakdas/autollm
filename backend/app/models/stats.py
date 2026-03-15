"""Aggregated statistics models."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FeatureStatsDaily(Base):
    __tablename__ = "feature_stats_daily"
    __table_args__ = (UniqueConstraint("feature_id", "stat_date", name="uq_feature_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("features.id", ondelete="CASCADE"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_cents: Mapped[float] = mapped_column(Float, default=0.0)
    total_savings_cents: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    rerouted_count: Mapped[int] = mapped_column(Integer, default=0)

    # Most-used model breakdown (top 3 stored as CSV for simplicity)
    top_models: Mapped[str | None] = mapped_column(String(512), nullable=True)

    feature: Mapped["Feature"] = relationship(back_populates="daily_stats")


class ProjectMonthlyUsage(Base):
    """Tracks monthly request count per project for plan-limit enforcement."""
    __tablename__ = "project_monthly_usage"
    __table_args__ = (UniqueConstraint("project_id", "year_month", name="uq_project_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-03"
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    limit_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="monthly_usage")
