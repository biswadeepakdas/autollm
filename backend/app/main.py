"""AutoLLM backend — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.auth_routes import router as auth_router
from app.api.project_routes import router as project_router
from app.api.feature_routes import router as feature_router
from app.api.ingest_routes import router as ingest_router
from app.api.suggestion_routes import router as suggestion_router
from app.api.billing_routes import router as billing_router
from app.api.stats_routes import router as stats_router

# Import all models so Base.metadata knows about them
import app.models  # noqa: F401

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default plans
    await _seed_plans()
    # Start background scheduler
    try:
        from app.worker.scheduler import start_scheduler
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler failed to start (non-fatal): {e}")
    yield
    await engine.dispose()


async def _seed_plans():
    """Insert default plans if they don't exist."""
    from sqlalchemy import select
    from app.database import async_session
    from app.models.plan import Plan, PLAN_DEFAULTS

    async with async_session() as session:
        for plan_data in PLAN_DEFAULTS:
            result = await session.execute(select(Plan).where(Plan.code == plan_data["code"]))
            if not result.scalar_one_or_none():
                session.add(Plan(**plan_data))
        await session.commit()
    logger.info("Plans seeded")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS - allow configured frontend + any extra origins
allowed_origins = [settings.FRONTEND_URL]
if settings.ALLOWED_ORIGINS:
    allowed_origins.extend([o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()])
if settings.ENVIRONMENT == "development":
    allowed_origins.extend(["http://localhost:3000", "http://localhost:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(feature_router)
app.include_router(ingest_router)
app.include_router(suggestion_router)
app.include_router(billing_router)
app.include_router(stats_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
