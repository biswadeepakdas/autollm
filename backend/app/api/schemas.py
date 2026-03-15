"""Pydantic schemas for request/response validation."""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_and_reject_empty(v: object, field_name: str) -> str:
    """Strip whitespace and reject whitespace-only strings."""
    if not isinstance(v, str):
        return v
    v = v.strip()
    if not v:
        raise ValueError(f"{field_name} must not be empty or whitespace-only")
    return v


def _sanitize_html(v: str) -> str:
    """Strip HTML tags to prevent XSS."""
    return re.sub(r'<[^>]+>', '', v)


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        if v is None:
            return v
        v = _strip_and_reject_empty(v, "name")
        return _sanitize_html(v)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v

class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=255)
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
    has_password: bool = True
    oauth_providers: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ── Projects ─────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_sanitize_name(cls, v):
        v = _strip_and_reject_empty(v, "name")
        return _sanitize_html(v)

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str = Field(max_length=100)
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
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_sanitize_name(cls, v):
        v = _strip_and_reject_empty(v, "name")
        return _sanitize_html(v)

class FeatureResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str = Field(max_length=100)
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
    preferred_model: Optional[str] = Field(default=None, max_length=100)
    preferred_provider: Optional[str] = Field(default=None, max_length=100)
    monthly_budget_cents: Optional[int] = None


# ── Ingestion ────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    feature: str = Field(max_length=100)  # feature slug
    provider: str = Field(max_length=100)
    model: str = Field(max_length=100)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    status_code: int = 200
    error: Optional[str] = Field(default=None, max_length=500)
    was_rerouted: bool = False
    original_model: Optional[str] = Field(default=None, max_length=100)
    reroute_reason: Optional[str] = Field(default=None, max_length=500)
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
    plan_code: str = Field(max_length=100)  # "plan_free", "plan_pro", "plan_max"


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
