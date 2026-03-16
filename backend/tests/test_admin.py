"""Tests for admin endpoints under /api/admin/."""

import pytest
from uuid import uuid4
from httpx import AsyncClient

from tests.conftest import TEST_USER_PASSWORD


async def _create_target_user(client: AsyncClient) -> dict:
    """Create a regular user inline (avoids fixture-ordering issues with admin).
    Clears cookies after registration so the admin's Bearer token takes priority."""
    email = f"target-{uuid4().hex[:8]}@example.com"
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": "targetpass123",
        "name": "Target User",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    data["_email"] = email
    # Clear cookies set by the registration response so they don't override
    # the Authorization header (Bearer token) used by admin tests.
    client.cookies.clear()
    return data


# ── Stats ─────────────────────────────────────────────────────────────────────

async def test_admin_stats_as_admin(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "users" in body
    assert "total_requests" in body
    assert "total_cost_cents" in body
    assert "projects" in body
    assert "plan_distribution" in body
    assert body["users"] >= 1


async def test_admin_stats_as_non_admin(client: AsyncClient, auth_headers: dict):
    """Regular user should get 403 on admin endpoints."""
    resp = await client.get("/api/admin/stats", headers=auth_headers)
    assert resp.status_code == 403
    assert "admin" in resp.json()["detail"].lower()


# ── Users list ────────────────────────────────────────────────────────────────

async def test_admin_users_list(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "users" in body
    assert "total" in body
    assert "page" in body
    assert "per_page" in body
    assert "pages" in body
    assert body["total"] >= 1
    assert len(body["users"]) >= 1
    # Each user item should have expected fields
    u = body["users"][0]
    assert "id" in u
    assert "email" in u
    assert "is_admin" in u


# ── Change user plan ─────────────────────────────────────────────────────────

async def test_admin_change_user_plan(client: AsyncClient, admin_headers: dict):
    """Admin can change another user's plan."""
    target = await _create_target_user(client)
    user_id = target["user"]["id"]

    resp = await client.patch(
        f"/api/admin/users/{user_id}/plan?plan_code=plan_pro",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["plan"] == "Pro"


# ── Toggle admin ──────────────────────────────────────────────────────────────

async def test_admin_toggle_admin(client: AsyncClient, admin_headers: dict):
    """Admin can toggle admin status of another user."""
    target = await _create_target_user(client)
    user_id = target["user"]["id"]

    resp = await client.patch(
        f"/api/admin/users/{user_id}/admin",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "is_admin" in body


# ── Cannot remove own admin status ───────────────────────────────────────────

async def test_admin_cannot_remove_own_admin(client: AsyncClient, admin_user: dict, admin_headers: dict):
    """Admin should not be able to toggle their own admin status."""
    admin_id = admin_user["user"]["id"]

    resp = await client.patch(
        f"/api/admin/users/{admin_id}/admin",
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "own" in resp.json()["detail"].lower()


# ── User not found ───────────────────────────────────────────────────────────

async def test_admin_user_not_found(client: AsyncClient, admin_headers: dict):
    fake_id = str(uuid4())
    resp = await client.patch(
        f"/api/admin/users/{fake_id}/plan?plan_code=plan_pro",
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ── Invalid plan code ────────────────────────────────────────────────────────

async def test_admin_invalid_plan_code(client: AsyncClient, admin_headers: dict):
    target = await _create_target_user(client)
    user_id = target["user"]["id"]
    resp = await client.patch(
        f"/api/admin/users/{user_id}/plan?plan_code=plan_nonexistent",
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()
