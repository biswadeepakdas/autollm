"""LLM request log model — the core data table for cost tracking."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMRequest(Base):
    __tablename__ = "llm_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("features.id", ondelete="SET NULL"), nullable=True, index=True)

    # ── Provider & model ─────────────────────────────────────────────────
    provider: Mapped[str] = mapped_column(String(64), nullable=False)   # openai, anthropic, gemini, nvidia_nim
    model: Mapped[str] = mapped_column(String(128), nullable=False)     # gpt-4.1, claude-sonnet-4-20250514, etc.

    # ── Token counts ─────────────────────────────────────────────────────
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # ── Cost ─────────────────────────────────────────────────────────────
    cost_cents: Mapped[float] = mapped_column(Float, default=0.0)       # estimated cost in cents
    estimated_savings_cents: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Latency & status ─────────────────────────────────────────────────
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Auto mode metadata ───────────────────────────────────────────────
    was_rerouted: Mapped[bool] = mapped_column(default=False)
    original_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reroute_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # ── Raw payloads (optional, for debugging) ───────────────────────────
    request_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
