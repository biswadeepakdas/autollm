"""Background aggregation job — rolls up LLM requests into daily stats."""

from datetime import date, datetime, timezone, timedelta
import asyncio

from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models.llm_request import LLMRequest
from app.models.feature import Feature
from app.models.stats import FeatureStatsDaily
from app.models.project import Project


async def aggregate_daily_stats(target_date: date | None = None):
    """Aggregate yesterday's LLM requests into FeatureStatsDaily rows.
    Run once daily via scheduler or Celery beat.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    async with async_session() as db:
        # Get all features that had traffic on target_date
        result = await db.execute(
            select(
                LLMRequest.feature_id,
                func.count().label("total_requests"),
                func.sum(LLMRequest.total_tokens).label("total_tokens"),
                func.sum(LLMRequest.cost_cents).label("total_cost_cents"),
                func.sum(LLMRequest.estimated_savings_cents).label("total_savings_cents"),
                func.avg(LLMRequest.latency_ms).label("avg_latency_ms"),
                func.sum(func.cast(LLMRequest.status_code >= 400, type_=func.literal_column("int"))).label("error_count"),
                func.sum(func.cast(LLMRequest.was_rerouted, type_=func.literal_column("int"))).label("rerouted_count"),
            )
            .where(
                LLMRequest.feature_id.isnot(None),
                LLMRequest.created_at >= start,
                LLMRequest.created_at < end,
            )
            .group_by(LLMRequest.feature_id)
        )

        rows = result.all()
        for row in rows:
            # Upsert into feature_stats_daily
            existing = await db.execute(
                select(FeatureStatsDaily).where(
                    FeatureStatsDaily.feature_id == row.feature_id,
                    FeatureStatsDaily.stat_date == target_date,
                )
            )
            stat = existing.scalar_one_or_none()
            if stat:
                stat.total_requests = int(row.total_requests or 0)
                stat.total_tokens = int(row.total_tokens or 0)
                stat.total_cost_cents = float(row.total_cost_cents or 0)
                stat.total_savings_cents = float(row.total_savings_cents or 0)
                stat.avg_latency_ms = float(row.avg_latency_ms or 0)
                stat.error_count = int(row.error_count or 0)
                stat.rerouted_count = int(row.rerouted_count or 0)
            else:
                stat = FeatureStatsDaily(
                    feature_id=row.feature_id,
                    stat_date=target_date,
                    total_requests=int(row.total_requests or 0),
                    total_tokens=int(row.total_tokens or 0),
                    total_cost_cents=float(row.total_cost_cents or 0),
                    total_savings_cents=float(row.total_savings_cents or 0),
                    avg_latency_ms=float(row.avg_latency_ms or 0),
                    error_count=int(row.error_count or 0),
                    rerouted_count=int(row.rerouted_count or 0),
                )
                db.add(stat)

        # Find top models per feature
        for row in rows:
            top_result = await db.execute(
                select(LLMRequest.model, func.count().label("cnt"))
                .where(
                    LLMRequest.feature_id == row.feature_id,
                    LLMRequest.created_at >= start,
                    LLMRequest.created_at < end,
                )
                .group_by(LLMRequest.model)
                .order_by(func.count().desc())
                .limit(3)
            )
            top_models = [r.model for r in top_result]
            stat_result = await db.execute(
                select(FeatureStatsDaily).where(
                    FeatureStatsDaily.feature_id == row.feature_id,
                    FeatureStatsDaily.stat_date == target_date,
                )
            )
            stat = stat_result.scalar_one_or_none()
            if stat:
                stat.top_models = ",".join(top_models)

        await db.commit()
        print(f"[Aggregator] Processed {len(rows)} features for {target_date}")


def run_aggregation(target_date: date | None = None):
    """Synchronous wrapper for running from Celery or CLI."""
    asyncio.run(aggregate_daily_stats(target_date))
