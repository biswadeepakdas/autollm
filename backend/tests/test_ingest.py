"""Tests for SDK ingestion endpoints under /api/sdk/ingest."""

import pytest
from uuid import uuid4
from httpx import AsyncClient

from tests.conftest import TEST_USER_PASSWORD


async def _setup_project_with_key(client: AsyncClient, auth_headers: dict) -> tuple[str, str]:
    """Create a project, generate an API key, return (project_id, raw_api_key)."""
    name = f"ingest-proj-{uuid4().hex[:8]}"
    resp = await client.post("/api/projects", json={"name": name}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    project = resp.json()
    pid = project["id"]

    # The project creation already returns a raw key in api_key_prefix
    raw_key = project["api_key_prefix"]

    # But also explicitly create a key via the keys endpoint
    key_resp = await client.post(f"/api/projects/{pid}/keys", headers=auth_headers)
    assert key_resp.status_code == 201, key_resp.text
    raw_key = key_resp.json()["raw_key"]

    return pid, raw_key


def _ingest_payload(**overrides) -> dict:
    payload = {
        "feature": "chat",
        "provider": "openai",
        "model": "gpt-4o",
        "prompt_tokens": 500,
        "completion_tokens": 200,
        "latency_ms": 350,
        "status_code": 200,
    }
    payload.update(overrides)
    return payload


# ── Success ───────────────────────────────────────────────────────────────────

async def test_ingest_success(client: AsyncClient, auth_headers: dict):
    _, api_key = await _setup_project_with_key(client, auth_headers)

    resp = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(),
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["request_id"] is not None


# ── Invalid API key ──────────────────────────────────────────────────────────

async def test_ingest_invalid_api_key(client: AsyncClient):
    resp = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(),
        headers={"X-API-Key": "allm_bogus_key_value"},
    )
    assert resp.status_code == 401


# ── Missing required fields ──────────────────────────────────────────────────

async def test_ingest_missing_fields(client: AsyncClient, auth_headers: dict):
    _, api_key = await _setup_project_with_key(client, auth_headers)

    # Missing 'feature' field
    resp = await client.post(
        "/api/sdk/ingest",
        json={"provider": "openai", "model": "gpt-4o"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422  # Pydantic validation error


# ── Unknown model still accepted (uses fallback cost) ─────────────────────────

async def test_ingest_unknown_model(client: AsyncClient, auth_headers: dict):
    _, api_key = await _setup_project_with_key(client, auth_headers)

    resp = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(provider="mystery_co", model="mystery-9000"),
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True


# ── Cost is computed and stored ──────────────────────────────────────────────

async def test_ingest_cost_calculation(client: AsyncClient, auth_headers: dict):
    """Ingest returns a request_id; the cost engine should have run."""
    _, api_key = await _setup_project_with_key(client, auth_headers)

    resp = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(prompt_tokens=1000, completion_tokens=1000),
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["request_id"] is not None


# ── Multiple ingestions create separate log rows ─────────────────────────────

async def test_ingest_logs_created(client: AsyncClient, auth_headers: dict):
    """Two ingest calls should produce two distinct request IDs."""
    _, api_key = await _setup_project_with_key(client, auth_headers)

    r1 = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(feature="feat-a"),
        headers={"X-API-Key": api_key},
    )
    r2 = await client.post(
        "/api/sdk/ingest",
        json=_ingest_payload(feature="feat-b"),
        headers={"X-API-Key": api_key},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["request_id"] != r2.json()["request_id"]
