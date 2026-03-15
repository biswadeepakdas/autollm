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
from app.api.password_reset_routes import router as password_reset_router
from app.api.webhooks import router as webhooks_router
from app.api.admin_routes import router as admin_router

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
    # Create/update tables on startup (safe: create_all is idempotent for new tables)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Add missing columns to existing tables (create_all doesn't ALTER existing tables)
    await _apply_schema_updates()
    # Seed default plans
    await _seed_plans()
    # Start background scheduler
    try:
        from app.worker.scheduler import start_scheduler
        start_scheduler()
        logger.info("Background scheduler started")
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")
    yield
    await engine.dispose()


async def _apply_schema_updates():
    """Add columns that create_all can't add to existing tables."""
    from sqlalchemy import text
    from app.database import async_session

    migrations = [
        ("users", "is_admin", "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"),
        ("users", "is_email_verified", "ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT FALSE"),
    ]
    async with async_session() as session:
        for table, column, sql in migrations:
            try:
                await session.execute(text(
                    f"SELECT {column} FROM {table} LIMIT 0"
                ))
            except Exception:
                await session.rollback()
                try:
                    await session.execute(text(sql))
                    await session.commit()
                    logger.info(f"Added column {table}.{column}")
                except Exception as e:
                    await session.rollback()
                    logger.warning(f"Could not add {table}.{column}: {e}")


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

# ── Rate limiting ─────────────────────────────────────────────────────────────
try:
    from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled")
except Exception as e:
    logger.warning(f"Rate limiting not available: {e}")

# ── CORS ──────────────────────────────────────────────────────────────────────
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

# ── Register routers ─────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(feature_router)
app.include_router(ingest_router)
app.include_router(suggestion_router)
app.include_router(billing_router)
app.include_router(stats_router)
app.include_router(password_reset_router)
app.include_router(webhooks_router)
app.include_router(admin_router)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    from app.database import async_session

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "connected",
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "database": "disconnected",
            },
        )


@app.get("/api/config")
async def public_config():
    """Public config for the frontend — which features are available."""
    return {
        "google_oauth": bool(settings.GOOGLE_CLIENT_ID),
        "stripe_enabled": bool(settings.STRIPE_SECRET_KEY),
    }
