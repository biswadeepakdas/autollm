"""Tests for authentication endpoints: register, login, and /me."""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_PASSWORD, TEST_USER_NAME


# ── Registration ──────────────────────────────────────────────────────────────

async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "register_success@example.com",
        "password": "strongpassword1",
        "name": "New User",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["user"]["email"] == "register_success@example.com"
    assert body["user"]["name"] == "New User"
    # Free plan should be assigned automatically
    assert body["user"]["plan_code"] == "plan_free"


async def test_register_duplicate_email(client: AsyncClient):
    """Attempting to register with an already-used email returns 409."""
    email = "dup_check@example.com"
    # First registration succeeds
    resp1 = await client.post("/api/auth/register", json={
        "email": email,
        "password": "somepassword1",
        "name": "First",
    })
    assert resp1.status_code == 200

    # Second registration with same email fails
    resp2 = await client.post("/api/auth/register", json={
        "email": email,
        "password": "anotherpassword1",
        "name": "Duplicate",
    })
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client: AsyncClient, test_user: dict):
    email = test_user["_email"]
    resp = await client.post("/api/auth/login", json={
        "email": email,
        "password": TEST_USER_PASSWORD,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == email


async def test_login_wrong_password(client: AsyncClient, test_user: dict):
    resp = await client.post("/api/auth/login", json={
        "email": test_user["_email"],
        "password": "wrongpassword",
    })
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


# ── /me ───────────────────────────────────────────────────────────────────────

async def test_me_authenticated(client: AsyncClient, auth_headers: dict, test_user: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == test_user["_email"]
    assert body["name"] == TEST_USER_NAME


async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
