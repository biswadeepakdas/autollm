"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: "UserResponse"

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]
    plan_name: Optional[str] = None
    plan_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Projects ─────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    api_key_prefix: Optional[str] = None

    class Config:
        from_attributes = True

class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    label: str
    is_active: bool
    created_at: datetime
    raw_key: Optional[str] = None  # only returned on creation

    class Config:
        from_attributes = True


# ── Features ─────────────────────────────────────────────────────────────────

class CreateFeatureRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)

class FeatureResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    auto_mode: bool = False
    max_tokens_cap: Optional[int] = None
    preferred_model: Optional[str] = None
    preferred_provider: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateFeatureSettingsRequest(BaseModel):
    auto_mode: Optional[bool] = None
    max_tokens_cap: Optional[int] = None
    preferred_model: Optional[str] = None
    preferred_provider: Optional[str] = None
    monthly_budget_cents: Optional[int] = None


# ── Ingestion ────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    feature: str  # feature slug
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    status_code: int = 200
    error: Optional[str] = None
    was_rerouted: bool = False
    original_model: Optional[str] = None
    reroute_reason: Optional[str] = None
    request_metadata: Optional[dict] = None

class IngestResponse(BaseModel):
    accepted: bool
    request_id: Optional[uuid.UUID] = None
    message: Optional[str] = None


# ── Config (SDK) ─────────────────────────────────────────────────────────────

class SDKConfigResponse(BaseModel):
    project_id: uuid.UUID
    auto_mode_global: bool
    features: dict  # { slug: { auto_mode, max_tokens_cap, preferred_model, ... } }
    plan: dict      # plan name, limits, etc.


# ── Suggestions ──────────────────────────────────────────────────────────────

class SuggestionResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    description: str
    estimated_savings_cents: float
    confidence: float
    status: str
    priority: int
    feature_id: Optional[uuid.UUID]
    payload: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Plan / Usage ─────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    name: str
    code: str
    monthly_request_limit: int
    max_projects: int
    max_features_per_project: int
    auto_mode_enabled: bool
    price_monthly_cents: int

    class Config:
        from_attributes = True

class UsageResponse(BaseModel):
    plan: dict
    usage: dict
    limit_hit: bool

class ChangePlanRequest(BaseModel):
    plan_code: str  # "plan_free", "plan_pro", "plan_max"


# ── Project Settings ─────────────────────────────────────────────────────────

class UpdateProjectSettingsRequest(BaseModel):
    auto_mode_global: Optional[bool] = None
    monthly_budget_cents: Optional[int] = None
    default_max_tokens: Optional[int] = None


# ── Stats ────────────────────────────────────────────────────────────────────

class DailyStatsResponse(BaseModel):
    date: str
    total_requests: int
    total_tokens: int
    total_cost_cents: float
    total_savings_cents: float
    avg_latency_ms: float
    error_count: int
    rerouted_count: int
