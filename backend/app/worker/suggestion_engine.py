"""Suggestion engine — generates cost-saving recommendations (the 5 Auto mode rules)."""

import asyncio
import logging
from datetime import date, timedelta, timezone, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.llm_request import LLMRequest
from app.models.feature import Feature, FeatureSetting
from app.models.project import Project
from app.models.project_setting import ProjectSetting
from app.models.suggestion import Suggestion, SuggestionType, SuggestionStatus
from app.services.cost_engine import (
    CHEAPER_ALTERNATIVES, SMALL_PROMPT_THRESHOLD,
    estimate_cost_cents, MODEL_PRICING,
)

logger = logging.getLogger(__name__)


async def generate_suggestions():
    """Run all 5 suggestion rules across all projects. Run daily."""
    async with async_session() as db:
        result = await db.execute(select(Project))
        projects = result.scalars().all()

        for project in projects:
            try:
                await _rule_1_model_downgrade(db, project)
                await _rule_2_token_cap(db, project)
                await _rule_3_low_value_features(db, project)
                await _rule_4_provider_mix(db, project)
                await _rule_5_budget_alert(db, project)
            except Exception as e:
                logger.error(f"Error generating suggestions for project {project.id}: {e}")

        await db.commit()
        logger.info(f"Processed {len(projects)} projects for suggestions")


async def _rule_1_model_downgrade(db: AsyncSession, project: Project):
    """Rule 1: Suggest cheaper models for features with mostly small prompts."""
    since = date.today() - timedelta(days=7)

    result = await db.execute(
        select(
            LLMRequest.feature_id,
            LLMRequest.provider,
            LLMRequest.model,
            func.avg(LLMRequest.prompt_tokens).label("avg_prompt"),
            func.count().label("count"),
            func.sum(LLMRequest.cost_cents).label("total_cost"),
        )
        .where(
            LLMRequest.project_id == project.id,
            LLMRequest.created_at >= since,
            LLMRequest.feature_id.isnot(None),
        )
        .group_by(LLMRequest.feature_id, LLMRequest.provider, LLMRequest.model)
        .having(func.avg(LLMRequest.prompt_tokens) < SMALL_PROMPT_THRESHOLD)
        .having(func.count() >= 10)  # minimum sample size
    )

    for row in result:
        alternatives = CHEAPER_ALTERNATIVES.get((row.provider, row.model), [])
        if not alternatives:
            continue

        alt_provider, alt_model = alternatives[0]
        # Estimate savings
        avg_completion = 200  # reasonable default
        current_cost_per = estimate_cost_cents(row.provider, row.model, int(row.avg_prompt), avg_completion)
        alt_cost_per = estimate_cost_cents(alt_provider, alt_model, int(row.avg_prompt), avg_completion)
        savings_per = current_cost_per - alt_cost_per
        total_savings = savings_per * row.count * 4  # projected monthly

        if total_savings < 10:  # not worth suggesting under $0.10/month
            continue

        # Check if suggestion already exists
        existing = await db.execute(
            select(Suggestion).where(
                Suggestion.project_id == project.id,
                Suggestion.feature_id == row.feature_id,
                Suggestion.type == SuggestionType.MODEL_DOWNGRADE.value,
                Suggestion.status == SuggestionStatus.PENDING.value,
            )
        )
        if existing.scalar_one_or_none():
            continue

        suggestion = Suggestion(
            project_id=project.id,
            feature_id=row.feature_id,
            type=SuggestionType.MODEL_DOWNGRADE.value,
            title=f"Switch from {row.model} to {alt_model}",
            description=f"This feature averages {int(row.avg_prompt)} tokens/prompt — well under the threshold for {row.model}. Switching to {alt_model} could save ~${total_savings/100:.2f}/month with comparable quality for short prompts.",
            estimated_savings_cents=total_savings,
            confidence=0.85,
            priority=int(total_savings),
            payload={"from_model": row.model, "to_model": alt_model, "to_provider": alt_provider},
        )
        db.add(suggestion)


async def _rule_2_token_cap(db: AsyncSession, project: Project):
    """Rule 2: Suggest token caps for features with high completion variance."""
    since = date.today() - timedelta(days=7)

    result = await db.execute(
        select(
            LLMRequest.feature_id,
            func.avg(LLMRequest.completion_tokens).label("avg_comp"),
            func.max(LLMRequest.completion_tokens).label("max_comp"),
            func.count().label("count"),
        )
        .where(LLMRequest.project_id == project.id, LLMRequest.created_at >= since, LLMRequest.feature_id.isnot(None))
        .group_by(LLMRequest.feature_id)
        .having(func.count() >= 20)
    )

    for row in result:
        if row.max_comp and row.avg_comp and row.max_comp > row.avg_comp * 3:
            # High variance — suggest a cap at avg*2
            cap = int(row.avg_comp * 2)
            savings_estimate = (row.max_comp - cap) * 0.001 * row.count  # rough

            existing = await db.execute(
                select(Suggestion).where(
                    Suggestion.project_id == project.id,
                    Suggestion.feature_id == row.feature_id,
                    Suggestion.type == SuggestionType.TOKEN_CAP.value,
                    Suggestion.status == SuggestionStatus.PENDING.value,
                )
            )
            if existing.scalar_one_or_none():
                continue

            suggestion = Suggestion(
                project_id=project.id,
                feature_id=row.feature_id,
                type=SuggestionType.TOKEN_CAP.value,
                title=f"Set a token cap of {cap} tokens",
                description=f"Completions for this feature range from {int(row.avg_comp)} to {int(row.max_comp)} tokens. Setting a cap at {cap} (p95) would prevent outlier costs without affecting 95% of requests.",
                estimated_savings_cents=savings_estimate,
                confidence=0.75,
                priority=max(int(savings_estimate), 1),
                payload={"suggested_cap": cap, "avg_tokens": int(row.avg_comp), "max_tokens": int(row.max_comp)},
            )
            db.add(suggestion)


async def _rule_3_low_value_features(db: AsyncSession, project: Project):
    """Rule 3: Flag features with high cost but low usage."""
    since = date.today() - timedelta(days=30)

    result = await db.execute(
        select(
            LLMRequest.feature_id,
            func.count().label("count"),
            func.sum(LLMRequest.cost_cents).label("total_cost"),
        )
        .where(LLMRequest.project_id == project.id, LLMRequest.created_at >= since, LLMRequest.feature_id.isnot(None))
        .group_by(LLMRequest.feature_id)
    )
    rows = result.all()
    if not rows:
        return

    total_cost = sum(r.total_cost or 0 for r in rows)
    total_count = sum(r.count or 0 for r in rows)
    if total_cost == 0 or total_count == 0:
        return

    for row in rows:
        cost_share = (row.total_cost or 0) / total_cost
        usage_share = (row.count or 0) / total_count

        # High cost share (>20%) but low usage share (<5%)
        if cost_share > 0.20 and usage_share < 0.05:
            existing = await db.execute(
                select(Suggestion).where(
                    Suggestion.project_id == project.id,
                    Suggestion.feature_id == row.feature_id,
                    Suggestion.type == SuggestionType.LOW_VALUE_CUT.value,
                    Suggestion.status == SuggestionStatus.PENDING.value,
                )
            )
            if existing.scalar_one_or_none():
                continue

            suggestion = Suggestion(
                project_id=project.id,
                feature_id=row.feature_id,
                type=SuggestionType.LOW_VALUE_CUT.value,
                title=f"Review high-cost, low-traffic feature",
                description=f"This feature accounts for {cost_share*100:.0f}% of your LLM costs but only {usage_share*100:.1f}% of requests. Consider using a cheaper model or reviewing if this feature needs such an expensive model.",
                estimated_savings_cents=float(row.total_cost) * 0.5,
                confidence=0.7,
                priority=int(float(row.total_cost) * 0.5),
                payload={"cost_share": round(cost_share, 3), "usage_share": round(usage_share, 3)},
            )
            db.add(suggestion)


async def _rule_4_provider_mix(db: AsyncSession, project: Project):
    """Rule 4: Suggest cheaper cross-provider alternatives."""
    since = date.today() - timedelta(days=7)

    result = await db.execute(
        select(
            LLMRequest.provider,
            LLMRequest.model,
            func.count().label("count"),
            func.sum(LLMRequest.cost_cents).label("total_cost"),
            func.avg(LLMRequest.prompt_tokens).label("avg_prompt"),
            func.avg(LLMRequest.completion_tokens).label("avg_comp"),
        )
        .where(LLMRequest.project_id == project.id, LLMRequest.created_at >= since)
        .group_by(LLMRequest.provider, LLMRequest.model)
        .having(func.count() >= 10)
    )

    for row in result:
        # Check all alternatives (including cross-provider)
        alternatives = CHEAPER_ALTERNATIVES.get((row.provider, row.model), [])
        cross_provider = [a for a in alternatives if a[0] != row.provider]
        if not cross_provider:
            continue

        alt_provider, alt_model = cross_provider[0]
        current_per = estimate_cost_cents(row.provider, row.model, int(row.avg_prompt), int(row.avg_comp))
        alt_per = estimate_cost_cents(alt_provider, alt_model, int(row.avg_prompt), int(row.avg_comp))
        savings = (current_per - alt_per) * row.count * 4

        if savings < 50:
            continue

        existing = await db.execute(
            select(Suggestion).where(
                Suggestion.project_id == project.id,
                Suggestion.type == SuggestionType.PROVIDER_MIX.value,
                Suggestion.status == SuggestionStatus.PENDING.value,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        suggestion = Suggestion(
            project_id=project.id,
            type=SuggestionType.PROVIDER_MIX.value,
            title=f"Try {alt_provider}/{alt_model} instead of {row.provider}/{row.model}",
            description=f"A cross-provider switch from {row.model} to {alt_model} could save ~${savings/100:.2f}/month. Test quality with a small percentage of traffic first.",
            estimated_savings_cents=savings,
            confidence=0.6,
            priority=int(savings),
            payload={"from": f"{row.provider}/{row.model}", "to": f"{alt_provider}/{alt_model}"},
        )
        db.add(suggestion)


async def _rule_5_budget_alert(db: AsyncSession, project: Project):
    """Rule 5: Alert when monthly spending is on track to exceed budget."""
    result = await db.execute(
        select(ProjectSetting).where(ProjectSetting.project_id == project.id)
    )
    ps = result.scalar_one_or_none()
    if not ps or not ps.monthly_budget_cents:
        return

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_elapsed = (now - month_start).days + 1
    days_in_month = 30

    result = await db.execute(
        select(func.sum(LLMRequest.cost_cents))
        .where(LLMRequest.project_id == project.id, LLMRequest.created_at >= month_start)
    )
    spent = float(result.scalar() or 0)

    projected = (spent / days_elapsed) * days_in_month if days_elapsed > 0 else 0
    if projected > ps.monthly_budget_cents:
        overage = projected - ps.monthly_budget_cents

        existing = await db.execute(
            select(Suggestion).where(
                Suggestion.project_id == project.id,
                Suggestion.type == SuggestionType.BUDGET_ALERT.value,
                Suggestion.status == SuggestionStatus.PENDING.value,
            )
        )
        if existing.scalar_one_or_none():
            return

        suggestion = Suggestion(
            project_id=project.id,
            type=SuggestionType.BUDGET_ALERT.value,
            title=f"On track to exceed monthly budget by ${overage/100:.2f}",
            description=f"You've spent ${spent/100:.2f} in {days_elapsed} days. At this rate, you'll hit ${projected/100:.2f} by month end — ${overage/100:.2f} over your ${ps.monthly_budget_cents/100:.2f} budget. Consider enabling Auto mode to reduce costs.",
            estimated_savings_cents=overage * 0.3,
            confidence=0.9,
            priority=100,
            payload={"spent": spent, "projected": projected, "budget": ps.monthly_budget_cents},
        )
        db.add(suggestion)


def run_suggestion_engine():
    """Synchronous wrapper."""
    asyncio.run(generate_suggestions())
