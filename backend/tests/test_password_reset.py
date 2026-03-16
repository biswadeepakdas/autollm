"""Tests for password reset flow: forgot, verify, and reset."""

import hashlib
import secrets
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select

from tests.conftest import TEST_USER_PASSWORD


# ── Forgot password — existing user ─────────────────────────────────────────

async def test_forgot_password_success(client: AsyncClient, test_user: dict):
    """Forgot password for a real user should return ok (and not leak existence)."""
    with patch("app.api.password_reset_routes.send_password_reset_email", new_callable=AsyncMock, return_value=True):
        resp = await client.post("/api/auth/forgot-password", json={
            "email": test_user["_email"],
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "reset link" in body["message"].lower() or "sent" in body["message"].lower()


# ── Forgot password — nonexistent email still returns success ────────────────

async def test_forgot_password_nonexistent_email(client: AsyncClient):
    """To prevent email enumeration, we always return success."""
    resp = await client.post("/api/auth/forgot-password", json={
        "email": f"nobody-{uuid4().hex[:8]}@example.com",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ── Forgot password — invalid email format ───────────────────────────────────

async def test_forgot_password_invalid_email(client: AsyncClient):
    resp = await client.post("/api/auth/forgot-password", json={
        "email": "not-an-email",
    })
    assert resp.status_code == 422  # Pydantic validation


# ── Verify reset token — invalid token ───────────────────────────────────────

async def test_verify_reset_token_invalid(client: AsyncClient):
    resp = await client.post("/api/auth/verify-reset-token", json={
        "token": "totally-bogus-token",
    })
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


# ── Reset password — invalid token ───────────────────────────────────────────

async def test_reset_password_invalid_token(client: AsyncClient):
    resp = await client.post("/api/auth/reset-password", json={
        "token": "bogus-token",
        "new_password": "newpassword123",
    })
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()


# ── Reset password — full flow ───────────────────────────────────────────────

async def test_reset_password_success(client: AsyncClient, test_user: dict):
    """Full password-reset flow: create token in DB, call reset, then login."""
    from app.models.user import User
    from app.models.password_reset_token import PasswordResetToken
    from tests.conftest import TestSessionLocal

    # Use a separate session to insert the token (the client uses fresh sessions per request)
    async with TestSessionLocal() as db_session:
        # Find the user
        result = await db_session.execute(select(User).where(User.email == test_user["_email"]))
        user = result.scalar_one()

        # Create a valid reset token directly in the DB.
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db_session.add(reset_token)
        await db_session.commit()

    # Verify the token is valid
    verify_resp = await client.post("/api/auth/verify-reset-token", json={"token": raw_token})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True

    # Reset the password
    new_password = "brandnewpass456"
    reset_resp = await client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": new_password,
    })
    assert reset_resp.status_code == 200
    assert reset_resp.json()["ok"] is True

    # Login with the new password
    login_resp = await client.post("/api/auth/login", json={
        "email": test_user["_email"],
        "password": new_password,
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # Old password should no longer work
    old_login_resp = await client.post("/api/auth/login", json={
        "email": test_user["_email"],
        "password": TEST_USER_PASSWORD,
    })
    assert old_login_resp.status_code == 401
