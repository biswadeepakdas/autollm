"""Tests for billing endpoints: plan listing and subscription retrieval."""

import pytest
from httpx import AsyncClient


async def test_list_plans(client: AsyncClient):
    """GET /api/billing/plans should return the seeded plans (no auth required)."""
    resp = await client.get("/api/billing/plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) >= 3

    codes = {p["code"] for p in plans}
    assert "plan_free" in codes
    assert "plan_pro" in codes
    assert "plan_max" in codes

    # Verify Free plan details
    free = next(p for p in plans if p["code"] == "plan_free")
    assert free["name"] == "Free"
    assert free["price_monthly_cents"] == 0
    assert free["auto_mode_enabled"] is False
    assert free["monthly_request_limit"] == 5_000


async def test_get_subscription(client: AsyncClient, auth_headers: dict):
    """GET /api/billing/subscription returns the user's current plan."""
    resp = await client.get("/api/billing/subscription", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    # Newly registered user should be on the Free plan
    assert body["plan"] == "Free"
    assert body["code"] == "plan_free"
    assert body["status"] == "active"
    assert body["price_monthly_cents"] == 0
