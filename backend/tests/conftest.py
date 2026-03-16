"""Shared fixtures for the AutoLLM backend test suite.

Uses an in-memory SQLite database via aiosqlite so tests are fast,
self-contained, and require no external services (no Postgres, no Redis).
"""

import os
import sys
import uuid
from typing import AsyncGenerator
from unittest.mock import patch

# ---------------------------------------------------------------------------
# 0.  Set environment BEFORE any app code is imported.
# ---------------------------------------------------------------------------
os.environ["RATE_LIMIT_ENABLED"] = "0"
os.environ["REDIS_URL"] = "memory://"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "development"

# ---------------------------------------------------------------------------
# 0b. Patch logging for Python 3.14 compatibility.
#     Python 3.14 changed Logger._log() to reject unknown kwargs.  The app
#     uses structlog-style logger.info("msg", key=val) calls which pass kwargs
#     through to _log().  When structlog is not installed these fail.
#     We monkey-patch logging.Logger._log to silently drop extra kwargs.
# ---------------------------------------------------------------------------
import logging as _logging

_original_log = _logging.Logger._log


def _patched_log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **_kwargs):
    _original_log(self, level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)


_logging.Logger._log = _patched_log

# ---------------------------------------------------------------------------
# 1.  Patch PostgreSQL-only column types for SQLite compatibility.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


# ---------------------------------------------------------------------------
# 2.  Create the test engine BEFORE importing app.database.
#     app/database.py uses pool_size and max_overflow at module level, which
#     are invalid for SQLite.  We intercept the call by wrapping
#     create_async_engine to strip those kwargs when using SQLite.
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    create_async_engine as _real_create_async_engine,
    async_sessionmaker,
)

_SQLITE_UNSUPPORTED_POOL_KWARGS = {"pool_size", "max_overflow", "pool_pre_ping"}


def _patched_create_async_engine(url, **kwargs):
    """Drop pool-related kwargs when the URL targets SQLite."""
    url_str = str(url)
    if "sqlite" in url_str:
        kwargs = {k: v for k, v in kwargs.items() if k not in _SQLITE_UNSUPPORTED_POOL_KWARGS}
    return _real_create_async_engine(url_str, **kwargs)


# Patch before importing any app modules that use create_async_engine
import sqlalchemy.ext.asyncio as _sa_async  # noqa: E402
_original_cae = _sa_async.create_async_engine
_sa_async.create_async_engine = _patched_create_async_engine

# Also patch the import path that database.py uses directly
import sqlalchemy.ext.asyncio.engine as _sa_async_engine  # noqa: E402
_sa_async_engine.create_async_engine = _patched_create_async_engine

# ---------------------------------------------------------------------------
# 3.  Now import app modules — database.py will use patched engine creator.
# ---------------------------------------------------------------------------
from app.database import Base, get_db, engine as app_engine, async_session as app_session  # noqa: E402
from app.models.plan import Plan, PLAN_DEFAULTS  # noqa: E402
import app.models  # noqa: F401, E402
from app.main import app as fastapi_app  # noqa: E402

# Restore original create_async_engine (optional, for cleanliness)
_sa_async.create_async_engine = _original_cae
_sa_async_engine.create_async_engine = _original_cae

# The app_engine is now a SQLite engine; reuse it as the test engine.
test_engine = app_engine
TestSessionLocal = app_session

# ---------------------------------------------------------------------------
# 3b. Remove the request-logging middleware — it uses kwargs like method= and
#     path= that Python 3.14's stdlib Logger._log() no longer accepts.
# ---------------------------------------------------------------------------
fastapi_app.middleware_stack = None  # force rebuild
_to_remove = []
for m in fastapi_app.user_middleware:
    if "RequestLogging" in str(m):
        _to_remove.append(m)
for m in _to_remove:
    fastapi_app.user_middleware.remove(m)
fastapi_app.middleware_stack = None  # will be rebuilt on first request

# ---------------------------------------------------------------------------
# 4.  Fixtures
# ---------------------------------------------------------------------------
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _setup_db():
    """Create all tables once per test session and seed default plans."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed plans
    async with TestSessionLocal() as session:
        for plan_data in PLAN_DEFAULTS:
            session.add(Plan(**plan_data))
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture()
async def db_session(_setup_db) -> AsyncGenerator[AsyncSession, None]:
    """Yield a fresh session per test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(_setup_db) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client wired to the FastAPI app with the test DB.
    Each request gets a fresh session from the factory so identity-map
    caching never causes stale reads between requests."""

    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ── Convenience helpers ──────────────────────────────────────────────────────

TEST_USER_PASSWORD = "securepassword123"
TEST_USER_NAME = "Test User"

# Counter to generate unique emails per fixture invocation.
_user_counter = 0


def _next_email() -> str:
    global _user_counter
    _user_counter += 1
    return f"testuser{_user_counter}@example.com"


@pytest_asyncio.fixture()
async def test_user(client: AsyncClient) -> dict:
    """Register a unique user and return the parsed AuthResponse body."""
    email = _next_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": TEST_USER_PASSWORD,
        "name": TEST_USER_NAME,
    })
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    data = resp.json()
    # Stash email/password so downstream fixtures can use them.
    data["_email"] = email
    data["_password"] = TEST_USER_PASSWORD
    return data


@pytest_asyncio.fixture()
async def auth_headers(test_user: dict) -> dict:
    """Return Authorization headers with a valid JWT for the test user."""
    token = test_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Admin user fixtures ──────────────────────────────────────────────────────

_admin_counter = 0


def _next_admin_email() -> str:
    global _admin_counter
    _admin_counter += 1
    return f"admin{_admin_counter}@example.com"


@pytest_asyncio.fixture()
async def admin_user(client: AsyncClient) -> dict:
    """Register a user, promote to admin, then re-login to get a fresh token
    that is recognized as admin by the app."""
    email = _next_admin_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": TEST_USER_PASSWORD,
        "name": "Admin User",
    })
    assert resp.status_code == 200, f"Admin registration failed: {resp.text}"

    # Promote to admin directly in the DB using a separate session
    from sqlalchemy import select as sa_select
    from app.models.user import User as UserModel
    async with TestSessionLocal() as session:
        result = await session.execute(
            sa_select(UserModel).where(UserModel.email == email)
        )
        admin_obj = result.scalar_one()
        admin_obj.is_admin = True
        await session.commit()

    # Re-login to get a fresh token
    login_resp = await client.post("/api/auth/login", json={
        "email": email,
        "password": TEST_USER_PASSWORD,
    })
    assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
    data = login_resp.json()
    data["_email"] = email
    data["_password"] = TEST_USER_PASSWORD
    # Clear cookies so subsequent requests use the Authorization header
    client.cookies.clear()
    return data


@pytest_asyncio.fixture()
async def admin_headers(admin_user: dict) -> dict:
    """Return Authorization headers with a valid JWT for the admin user."""
    token = admin_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
