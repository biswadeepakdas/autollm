"""Project-level settings model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectSetting(Base):
    __tablename__ = "project_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    auto_mode_global: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_budget_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship(back_populates="settings")
