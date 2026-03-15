"""Feature management routes."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.project import Project
from app.models.feature import Feature, FeatureSetting
from app.services.plan_service import check_feature_limit, PlanLimitError, check_auto_mode_allowed
from app.api.schemas import CreateFeatureRequest, FeatureResponse, UpdateFeatureSettingsRequest

router = APIRouter(prefix="/api/projects/{project_id}/features", tags=["features"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:128] or "feature"


async def _verify_ownership(project_id: uuid.UUID, user, db) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _feature_response(f: Feature) -> FeatureResponse:
    return FeatureResponse(
        id=f.id,
        name=f.name,
        slug=f.slug,
        auto_mode=f.settings.auto_mode if f.settings else False,
        max_tokens_cap=f.settings.max_tokens_cap if f.settings else None,
        preferred_model=f.settings.preferred_model if f.settings else None,
        preferred_provider=f.settings.preferred_provider if f.settings else None,
        created_at=f.created_at,
    )


@router.post("", response_model=FeatureResponse, status_code=201)
async def create_feature(
    project_id: uuid.UUID,
    body: CreateFeatureRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_ownership(project_id, user, db)

    try:
        await check_feature_limit(db, user, project_id)
    except PlanLimitError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    slug = _slugify(body.name)
    feature = Feature(project_id=project_id, name=body.name, slug=slug)
    db.add(feature)
    await db.flush()

    fs = FeatureSetting(feature_id=feature.id)
    db.add(fs)
    await db.flush()

    feature.settings = fs
    return _feature_response(feature)


@router.get("", response_model=list[FeatureResponse])
async def list_features(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await _verify_ownership(project_id, user, db)
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Feature).options(selectinload(Feature.settings)).where(Feature.project_id == project_id).order_by(Feature.created_at)
    )
    features = result.scalars().all()
    return [_feature_response(f) for f in features]


@router.patch("/{feature_id}/settings")
async def update_feature_settings(
    project_id: uuid.UUID,
    feature_id: uuid.UUID,
    body: UpdateFeatureSettingsRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_ownership(project_id, user, db)

    result = await db.execute(
        select(FeatureSetting).where(FeatureSetting.feature_id == feature_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Feature not found")

    if body.auto_mode is not None:
        if body.auto_mode and not await check_auto_mode_allowed(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Auto mode requires a Pro or Max plan.",
            )
        fs.auto_mode = body.auto_mode

    if body.max_tokens_cap is not None:
        fs.max_tokens_cap = body.max_tokens_cap
    if body.preferred_model is not None:
        fs.preferred_model = body.preferred_model
    if body.preferred_provider is not None:
        fs.preferred_provider = body.preferred_provider
    if body.monthly_budget_cents is not None:
        fs.monthly_budget_cents = body.monthly_budget_cents

    return {"ok": True}


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(project_id: uuid.UUID, feature_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await _verify_ownership(project_id, user, db)
    result = await db.execute(select(Feature).where(Feature.id == feature_id, Feature.project_id == project_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    await db.delete(feature)
