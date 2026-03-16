"""Tests for input validation: registration, project, and feature schemas."""

import pytest
from uuid import uuid4
from httpx import AsyncClient


# ── Password validation ──────────────────────────────────────────────────────

async def test_register_weak_password_no_digits(client: AsyncClient):
    """Password without digits should be rejected."""
    resp = await client.post("/api/auth/register", json={
        "email": f"weak1-{uuid4().hex[:8]}@example.com",
        "password": "nodigitshere",
        "name": "Test",
    })
    assert resp.status_code == 422
    body = resp.json()
    detail_str = str(body).lower()
    assert "digit" in detail_str


async def test_register_short_password(client: AsyncClient):
    """Password shorter than 8 chars should be rejected."""
    resp = await client.post("/api/auth/register", json={
        "email": f"short-{uuid4().hex[:8]}@example.com",
        "password": "ab1",
        "name": "Test",
    })
    assert resp.status_code == 422


async def test_register_long_password(client: AsyncClient):
    """Password longer than 128 chars should be rejected."""
    long_pw = "a1" * 100  # 200 chars
    resp = await client.post("/api/auth/register", json={
        "email": f"long-{uuid4().hex[:8]}@example.com",
        "password": long_pw,
        "name": "Test",
    })
    assert resp.status_code == 422


async def test_register_invalid_email(client: AsyncClient):
    """Invalid email format should be rejected."""
    resp = await client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "validpass123",
        "name": "Test",
    })
    assert resp.status_code == 422


async def test_register_whitespace_name(client: AsyncClient):
    """Whitespace-only name should be rejected."""
    resp = await client.post("/api/auth/register", json={
        "email": f"ws-{uuid4().hex[:8]}@example.com",
        "password": "validpass123",
        "name": "   ",
    })
    assert resp.status_code == 422
    detail_str = str(resp.json()).lower()
    assert "empty" in detail_str or "whitespace" in detail_str


# ── Project name validation ──────────────────────────────────────────────────

async def test_create_project_empty_name(client: AsyncClient, auth_headers: dict):
    """Empty project name should be rejected."""
    resp = await client.post(
        "/api/projects",
        json={"name": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_create_project_long_name(client: AsyncClient, auth_headers: dict):
    """Project name over 100 chars should be rejected."""
    resp = await client.post(
        "/api/projects",
        json={"name": "X" * 150},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── Feature name XSS sanitization ────────────────────────────────────────────

async def test_create_feature_xss_name(client: AsyncClient, auth_headers: dict):
    """HTML tags in feature name should be stripped."""
    # Create a project first
    proj_resp = await client.post(
        "/api/projects",
        json={"name": f"xss-proj-{uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    pid = proj_resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{pid}/features",
        json={"name": "<b>Bold</b> Feature"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    # HTML tags should be stripped
    assert "<b>" not in body["name"]
    assert "</b>" not in body["name"]
    # The text content should remain
    assert "Bold" in body["name"]
    assert "Feature" in body["name"]
