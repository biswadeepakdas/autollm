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

    # Aggregate from daily stats
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
    row = result.one()

    # Daily breakdown
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

    # Top models by cost
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
            "cost_cents": float(row.total_cost or 0),
            "savings_cents": float(row.total_savings or 0),
            "request_count": int(row.total_requests or 0),
            "total_tokens": int(row.total_tokens or 0),
            "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            "total_errors": int(row.total_errors or 0),
            "total_rerouted": int(row.total_rerouted or 0),
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
