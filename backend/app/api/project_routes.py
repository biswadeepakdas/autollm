"""Project management routes."""

import hashlib
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.project import Project, ApiKey, generate_api_key
from app.models.project_setting import ProjectSetting
from app.services.plan_service import check_project_limit, PlanLimitError, get_usage_stats
from app.api.schemas import (
    CreateProjectRequest, ProjectResponse, ApiKeyResponse, UsageResponse,
    UpdateProjectSettingsRequest,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:128] if slug else "project"


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: CreateProjectRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        await check_project_limit(db, user)
    except PlanLimitError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    slug = _slugify(body.name)
    # Ensure slug uniqueness per user
    existing = await db.execute(
        select(Project).where(Project.owner_id == user.id, Project.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    project = Project(owner_id=user.id, name=body.name, slug=slug)
    db.add(project)
    await db.flush()

    # Create default settings
    ps = ProjectSetting(project_id=project.id)
    db.add(ps)

    # Create default API key
    raw_key = generate_api_key()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        project_id=project.id,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        label="Default",
    )
    db.add(api_key)
    await db.flush()

    return ProjectResponse(
        id=project.id, name=project.name, slug=project.slug,
        created_at=project.created_at, api_key_prefix=raw_key,  # full key on creation only
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [ProjectResponse(id=p.id, name=p.name, slug=p.slug, created_at=p.created_at) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(id=project.id, name=project.name, slug=project.slug, created_at=project.created_at)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)


# ── API Keys ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    # Verify ownership
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(ApiKey).where(ApiKey.project_id == project_id).order_by(ApiKey.created_at))
    keys = result.scalars().all()
    return [ApiKeyResponse(id=k.id, key_prefix=k.key_prefix, label=k.label, is_active=k.is_active, created_at=k.created_at) for k in keys]


@router.post("/{project_id}/keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    raw_key = generate_api_key()
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(project_id=project_id, key_hash=key_hash, key_prefix=raw_key[:12])
    db.add(api_key)
    await db.flush()
    return ApiKeyResponse(
        id=api_key.id, key_prefix=api_key.key_prefix, label=api_key.label,
        is_active=api_key.is_active, created_at=api_key.created_at, raw_key=raw_key,
    )


# ── Usage & Settings ─────────────────────────────────────────────────────────

@router.get("/{project_id}/usage", response_model=UsageResponse)
async def get_project_usage(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
    stats = await get_usage_stats(db, project_id, user)
    return UsageResponse(**stats)


@router.patch("/{project_id}/settings")
async def update_project_settings(
    project_id: uuid.UUID,
    body: UpdateProjectSettingsRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(ProjectSetting).where(ProjectSetting.project_id == project_id))
    ps = result.scalar_one_or_none()
    if not ps:
        ps = ProjectSetting(project_id=project_id)
        db.add(ps)
        await db.flush()

    # Check auto mode permission
    if body.auto_mode_global is not None:
        from app.services.plan_service import check_auto_mode_allowed
        if body.auto_mode_global and not await check_auto_mode_allowed(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Auto mode is only available on Pro and Max plans. Upgrade to enable it.",
            )
        ps.auto_mode_global = body.auto_mode_global

    if body.monthly_budget_cents is not None:
        ps.monthly_budget_cents = body.monthly_budget_cents
    if body.default_max_tokens is not None:
        ps.default_max_tokens = body.default_max_tokens

    return {"ok": True}
