"""Tests for project CRUD and API-key creation endpoints."""

import pytest
from httpx import AsyncClient


async def test_create_project(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/projects",
        json={"name": "My Project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Project"
    assert body["slug"] == "my-project"
    # On creation, the full API key is returned as api_key_prefix
    assert body["api_key_prefix"] is not None
    assert body["api_key_prefix"].startswith("allm_")


async def test_list_projects(client: AsyncClient, auth_headers: dict):
    # Create one project (Free plan allows 1 project)
    create_resp = await client.post(
        "/api/projects", json={"name": "Listed Project"}, headers=auth_headers,
    )
    assert create_resp.status_code == 201

    resp = await client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 1
    names = [p["name"] for p in projects]
    assert "Listed Project" in names


async def test_get_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/projects", json={"name": "Detail Project"}, headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detail Project"


async def test_delete_project(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/projects", json={"name": "To Delete"}, headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_create_api_key(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post(
        "/api/projects", json={"name": "Key Project"}, headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{project_id}/keys", headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["raw_key"] is not None
    assert body["raw_key"].startswith("allm_")
    assert body["is_active"] is True
