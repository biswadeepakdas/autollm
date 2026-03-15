"""Suggestion routes — view and manage cost-saving suggestions."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.deps import CurrentUser
from app.models.project import Project
from app.models.suggestion import Suggestion, SuggestionStatus
from app.api.schemas import SuggestionResponse

router = APIRouter(prefix="/api/projects/{project_id}/suggestions", tags=["suggestions"])


@router.get("", response_model=list[SuggestionResponse])
async def list_suggestions(project_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Suggestion)
        .where(Suggestion.project_id == project_id)
        .order_by(Suggestion.priority.desc(), Suggestion.created_at.desc())
        .limit(50)
    )
    suggestions = result.scalars().all()
    return [SuggestionResponse(
        id=s.id, type=s.type, title=s.title, description=s.description,
        estimated_savings_cents=s.estimated_savings_cents, confidence=s.confidence,
        status=s.status, priority=s.priority, feature_id=s.feature_id,
        payload=s.payload, created_at=s.created_at,
    ) for s in suggestions]


@router.patch("/{suggestion_id}")
async def update_suggestion(
    project_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    action: str,  # "accept" or "dismiss"
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id, Suggestion.project_id == project_id))
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if action == "accept":
        suggestion.status = SuggestionStatus.ACCEPTED.value
    elif action == "dismiss":
        suggestion.status = SuggestionStatus.DISMISSED.value
    else:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'dismiss'")

    suggestion.resolved_at = datetime.now(timezone.utc)
    return {"ok": True}
