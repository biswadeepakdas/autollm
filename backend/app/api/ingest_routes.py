"""Ingestion and SDK config endpoints — authenticated by API key."""

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.logging_config import get_logger

logger = get_logger(__name__)
from app.auth.deps import AuthedProject
from app.models.feature import Feature, FeatureSetting
from app.models.llm_request import LLMRequest
from app.models.project_setting import ProjectSetting
from app.services.plan_service import check_ingestion_limit, increment_usage, get_user_plan
from app.services.cost_engine import estimate_cost_cents, estimate_savings_cents
from app.api.schemas import IngestRequest, IngestResponse, SDKConfigResponse
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/sdk", tags=["sdk"])


# ── POST /ingest — log an LLM request ───────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("200/minute")
async def ingest(request: Request, body: IngestRequest, project: AuthedProject, db: AsyncSession = Depends(get_db)):
    # 1. Check ingestion limits
    within_limit = await check_ingestion_limit(db, project)
    if not within_limit:
        return IngestResponse(
            accepted=False,
            message="Monthly request limit reached. Upgrade your plan to continue logging.",
        )

    # 2. Resolve or create feature
    slug = re.sub(r"[^a-z0-9]+", "-", body.feature.lower()).strip("-")[:128]
    result = await db.execute(
        select(Feature).where(Feature.project_id == project.id, Feature.slug == slug)
    )
    feature = result.scalar_one_or_none()

    if not feature:
        # Auto-create features from SDK (check limit)
        from app.services.plan_service import check_feature_limit, PlanLimitError
        try:
            await check_feature_limit(db, project.owner, project.id)
        except PlanLimitError:
            return IngestResponse(
                accepted=False,
                message="Feature limit reached for this project. Upgrade your plan.",
            )
        feature = Feature(project_id=project.id, name=body.feature, slug=slug)
        db.add(feature)
        await db.flush()
        fs = FeatureSetting(feature_id=feature.id)
        db.add(fs)
        await db.flush()

    # 3. Compute cost & savings
    cost = estimate_cost_cents(body.provider, body.model, body.prompt_tokens, body.completion_tokens)
    savings = estimate_savings_cents(body.provider, body.model, body.prompt_tokens, body.completion_tokens)

    # 4. Store the request
    llm_req = LLMRequest(
        project_id=project.id,
        feature_id=feature.id,
        provider=body.provider,
        model=body.model,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
        total_tokens=body.total_tokens or (body.prompt_tokens + body.completion_tokens),
        cost_cents=cost,
        estimated_savings_cents=savings,
        latency_ms=body.latency_ms,
        status_code=body.status_code,
        error=body.error,
        was_rerouted=body.was_rerouted,
        original_model=body.original_model,
        reroute_reason=body.reroute_reason,
        request_metadata=body.request_metadata,
    )
    db.add(llm_req)

    # 5. Increment usage
    usage = await increment_usage(db, project.id)

    # 6. Check if limit just hit
    plan = await get_user_plan(db, project.owner)
    if usage.request_count >= plan.monthly_request_limit and not usage.limit_hit_at:
        usage.limit_hit_at = datetime.now(timezone.utc)

    await db.flush()

    logger.info(
        "llm_request_ingested",
        project_id=str(project.id),
        feature=body.feature,
        provider=body.provider,
        model=body.model,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
        cost_cents=cost,
        latency_ms=body.latency_ms,
    )

    return IngestResponse(accepted=True, request_id=llm_req.id)


# ── GET /config — SDK fetches project config ─────────────────────────────────

@router.get("/config", response_model=SDKConfigResponse)
@limiter.limit("60/minute")
async def get_config(request: Request, project: AuthedProject, db: AsyncSession = Depends(get_db)):
    # Load project settings
    result = await db.execute(
        select(ProjectSetting).where(ProjectSetting.project_id == project.id)
    )
    ps = result.scalar_one_or_none()

    # Load features with settings
    result = await db.execute(
        select(Feature).options(selectinload(Feature.settings)).where(Feature.project_id == project.id)
    )
    features = result.scalars().all()

    # Build features config map
    features_config = {}
    for f in features:
        features_config[f.slug] = {
            "auto_mode": f.settings.auto_mode if f.settings else False,
            "max_tokens_cap": f.settings.max_tokens_cap if f.settings else None,
            "preferred_model": f.settings.preferred_model if f.settings else None,
            "preferred_provider": f.settings.preferred_provider if f.settings else None,
        }

    plan = await get_user_plan(db, project.owner)

    return SDKConfigResponse(
        project_id=project.id,
        auto_mode_global=ps.auto_mode_global if ps else False,
        features=features_config,
        plan={
            "name": plan.name,
            "code": plan.code,
            "auto_mode_enabled": plan.auto_mode_enabled,
            "monthly_request_limit": plan.monthly_request_limit,
        },
    )
