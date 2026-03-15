"""Dashboard statistics routes."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.project import Project
from app.models.llm_request import LLMRequest
from app.models.stats import FeatureStatsDaily
from app.models.feature import Feature
from app.api.schemas import DailyStatsResponse

router = APIRouter(prefix="/api/projects/{project_id}/stats", tags=["stats"])


def _pct_change(current: float, previous: float) -> float | None:
    """Return percentage change from previous to current, or None if no previous data."""
    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 1)


@router.get("/overview")
async def get_overview(
    project_id: uuid.UUID,
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """High-level dashboard overview stats."""
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    since = date.today() - timedelta(days=days)

    # --- Current period aggregates ---
    result = await db.execute(
        select(
            func.sum(FeatureStatsDaily.total_requests).label("total_requests"),
            func.sum(FeatureStatsDaily.total_tokens).label("total_tokens"),
            func.sum(FeatureStatsDaily.total_cost_cents).label("total_cost"),
            func.sum(FeatureStatsDaily.total_savings_cents).label("total_savings"),
            func.avg(FeatureStatsDaily.avg_latency_ms).label("avg_latency"),
            func.sum(FeatureStatsDaily.error_count).label("total_errors"),
            func.sum(FeatureStatsDaily.rerouted_count).label("total_rerouted"),
        )
        .join(Feature, Feature.id == FeatureStatsDaily.feature_id)
        .where(Feature.project_id == project_id, FeatureStatsDaily.stat_date >= since)
    )
    row = result.mappings().first()

    total_requests = int(row["total_requests"] or 0) if row else 0
    total_tokens = int(row["total_tokens"] or 0) if row else 0
    total_cost = float(row["total_cost"] or 0) if row else 0.0
    total_savings = float(row["total_savings"] or 0) if row else 0.0
    avg_latency = round(float(row["avg_latency"] or 0), 1) if row else 0.0
    total_errors = int(row["total_errors"] or 0) if row else 0
    total_rerouted = int(row["total_rerouted"] or 0) if row else 0

    # --- Previous period aggregates (for trend calculation) ---
    prev_start = since - timedelta(days=days)
    result = await db.execute(
        select(
            func.sum(FeatureStatsDaily.total_requests).label("total_requests"),
            func.sum(FeatureStatsDaily.total_cost_cents).label("total_cost"),
        )
        .join(Feature, Feature.id == FeatureStatsDaily.feature_id)
        .where(
            Feature.project_id == project_id,
            FeatureStatsDaily.stat_date >= prev_start,
            FeatureStatsDaily.stat_date < since,
        )
    )
    prev_row = result.mappings().first()
    prev_requests = float(prev_row["total_requests"] or 0) if prev_row else 0.0
    prev_cost = float(prev_row["total_cost"] or 0) if prev_row else 0.0

    cost_trend = _pct_change(total_cost, prev_cost)
    request_trend = _pct_change(total_requests, prev_requests)

    # p95 latency: approximate as avg * 1.5 when we only have averaged daily data
    p95_latency_ms = round(avg_latency * 1.5, 1) if avg_latency else None

    # --- Daily breakdown ---
    result = await db.execute(
        select(
            FeatureStatsDaily.stat_date,
            func.sum(FeatureStatsDaily.total_requests).label("requests"),
            func.sum(FeatureStatsDaily.total_cost_cents).label("cost"),
            func.sum(FeatureStatsDaily.total_savings_cents).label("savings"),
        )
        .join(Feature, Feature.id == FeatureStatsDaily.feature_id)
        .where(Feature.project_id == project_id, FeatureStatsDaily.stat_date >= since)
        .group_by(FeatureStatsDaily.stat_date)
        .order_by(FeatureStatsDaily.stat_date)
    )
    daily = [{"date": str(r.stat_date), "requests": r.requests or 0, "cost_cents": float(r.cost or 0), "savings_cents": float(r.savings or 0)} for r in result]

    # --- Top models by cost ---
    result = await db.execute(
        select(
            LLMRequest.provider,
            LLMRequest.model,
            func.count().label("count"),
            func.sum(LLMRequest.cost_cents).label("total_cost"),
        )
        .where(LLMRequest.project_id == project_id, LLMRequest.created_at >= since)
        .group_by(LLMRequest.provider, LLMRequest.model)
        .order_by(func.sum(LLMRequest.cost_cents).desc())
        .limit(10)
    )
    top_models = [{"provider": r.provider, "model": r.model, "count": r.count, "cost_cents": float(r.total_cost or 0)} for r in result]

    return {
        "totals": {
            "cost_cents": total_cost,
            "cost_trend": cost_trend,
            "savings_cents": total_savings,
            "request_count": total_requests,
            "request_trend": request_trend,
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency_ms,
            "total_errors": total_errors,
            "total_rerouted": total_rerouted,
        },
        "daily": daily,
        "top_models": top_models,
    }


@router.get("/features")
async def get_feature_stats(
    project_id: uuid.UUID,
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Per-feature breakdown."""
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    since = date.today() - timedelta(days=days)

    result = await db.execute(
        select(
            Feature.id,
            Feature.name,
            Feature.slug,
            func.sum(FeatureStatsDaily.total_requests).label("requests"),
            func.sum(FeatureStatsDaily.total_cost_cents).label("cost"),
            func.sum(FeatureStatsDaily.total_savings_cents).label("savings"),
            func.avg(FeatureStatsDaily.avg_latency_ms).label("latency"),
        )
        .join(FeatureStatsDaily, FeatureStatsDaily.feature_id == Feature.id, isouter=True)
        .where(Feature.project_id == project_id)
        .where((FeatureStatsDaily.stat_date >= since) | (FeatureStatsDaily.stat_date == None))
        .group_by(Feature.id, Feature.name, Feature.slug)
        .order_by(func.sum(FeatureStatsDaily.total_cost_cents).desc().nullslast())
    )
    features = [{
        "id": str(r.id), "name": r.name, "slug": r.slug,
        "requests": int(r.requests or 0), "cost_cents": float(r.cost or 0),
        "savings_cents": float(r.savings or 0), "avg_latency_ms": float(r.latency or 0),
    } for r in result]

    return {"features": features}
