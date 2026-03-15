"""Plan enforcement — the single place that checks all plan limits."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanCode, UserSubscription
from app.models.project import Project
from app.models.feature import Feature
from app.models.stats import ProjectMonthlyUsage
from app.models.user import User


class PlanLimitError(Exception):
    """Raised when a plan limit is exceeded."""
    def __init__(self, message: str, limit_type: str, current: int, maximum: int):
        super().__init__(message)
        self.limit_type = limit_type
        self.current = current
        self.maximum = maximum


async def get_user_plan(db: AsyncSession, user: User) -> Plan:
    """Return the Plan for a user. Falls back to Free if no subscription."""
    if user.subscription and user.subscription.plan:
        return user.subscription.plan
    # Fallback: fetch Free plan
    result = await db.execute(select(Plan).where(Plan.code == PlanCode.FREE.value))
    return result.scalar_one()


async def check_project_limit(db: AsyncSession, user: User) -> None:
    """Raise if user has reached their plan's project limit."""
    plan = await get_user_plan(db, user)
    result = await db.execute(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id)
    )
    count = result.scalar() or 0
    if count >= plan.max_projects:
        raise PlanLimitError(
            f"Your {plan.name} plan allows up to {plan.max_projects} project(s). Upgrade to add more.",
            limit_type="max_projects",
            current=count,
            maximum=plan.max_projects,
        )


async def check_feature_limit(db: AsyncSession, user: User, project_id) -> None:
    """Raise if project has reached its plan's feature limit."""
    plan = await get_user_plan(db, user)
    result = await db.execute(
        select(func.count()).select_from(Feature).where(Feature.project_id == project_id)
    )
    count = result.scalar() or 0
    if count >= plan.max_features_per_project:
        raise PlanLimitError(
            f"Your {plan.name} plan allows up to {plan.max_features_per_project} features per project.",
            limit_type="max_features_per_project",
            current=count,
            maximum=plan.max_features_per_project,
        )


async def check_ingestion_limit(db: AsyncSession, project: Project) -> bool:
    """Check whether the project can still ingest requests this month.
    Returns True if within limit, False if exceeded.
    """
    user = project.owner
    plan = await get_user_plan(db, user)
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y-%m")

    result = await db.execute(
        select(ProjectMonthlyUsage).where(
            ProjectMonthlyUsage.project_id == project.id,
            ProjectMonthlyUsage.year_month == year_month,
        )
    )
    usage = result.scalar_one_or_none()
    if not usage:
        return True  # no usage yet this month
    return usage.request_count < plan.monthly_request_limit


async def increment_usage(db: AsyncSession, project_id, count: int = 1) -> ProjectMonthlyUsage:
    """Increment monthly usage counter. Creates row if needed."""
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y-%m")

    result = await db.execute(
        select(ProjectMonthlyUsage).where(
            ProjectMonthlyUsage.project_id == project_id,
            ProjectMonthlyUsage.year_month == year_month,
        )
    )
    usage = result.scalar_one_or_none()
    if not usage:
        usage = ProjectMonthlyUsage(project_id=project_id, year_month=year_month, request_count=0)
        db.add(usage)
        await db.flush()

    usage.request_count += count
    return usage


async def get_usage_stats(db: AsyncSession, project_id, user: User) -> dict:
    """Return current usage vs limits for display."""
    plan = await get_user_plan(db, user)
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y-%m")

    result = await db.execute(
        select(ProjectMonthlyUsage).where(
            ProjectMonthlyUsage.project_id == project_id,
            ProjectMonthlyUsage.year_month == year_month,
        )
    )
    usage = result.scalar_one_or_none()
    request_count = usage.request_count if usage else 0

    result = await db.execute(
        select(func.count()).select_from(Feature).where(Feature.project_id == project_id)
    )
    feature_count = result.scalar() or 0

    result = await db.execute(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id)
    )
    project_count = result.scalar() or 0

    return {
        "plan": {
            "name": plan.name,
            "code": plan.code,
            "auto_mode_enabled": plan.auto_mode_enabled,
            "price_monthly_cents": plan.price_monthly_cents,
        },
        "usage": {
            "requests": {"current": request_count, "limit": plan.monthly_request_limit},
            "projects": {"current": project_count, "limit": plan.max_projects},
            "features": {"current": feature_count, "limit": plan.max_features_per_project},
        },
        "limit_hit": usage.limit_hit_at is not None if usage else False,
    }


async def check_auto_mode_allowed(db: AsyncSession, user: User) -> bool:
    """Returns True if user's plan allows Auto mode."""
    plan = await get_user_plan(db, user)
    return plan.auto_mode_enabled
