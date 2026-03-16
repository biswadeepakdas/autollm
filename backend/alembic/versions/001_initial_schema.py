"""Initial schema — all tables for AutoLLM.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("password_hash", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── oauth_accounts ────────────────────────────────────────────────────
    op.create_table(
        "oauth_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_user_id", sa.String(256), nullable=False),
        sa.Column("provider_email", sa.String(320), nullable=True),
        sa.Column("access_token", sa.String(2048), nullable=True),
        sa.Column("refresh_token", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    # ── plans ─────────────────────────────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("monthly_request_limit", sa.Integer(), nullable=False),
        sa.Column("max_projects", sa.Integer(), nullable=False),
        sa.Column("max_features_per_project", sa.Integer(), nullable=False),
        sa.Column("auto_mode_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("price_monthly_cents", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("stripe_price_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    # ── user_subscriptions ────────────────────────────────────────────────
    op.create_table(
        "user_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'"), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(256), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"], unique=True)

    # ── projects ──────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # ── project_settings ──────────────────────────────────────────────────
    op.create_table(
        "project_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auto_mode_global", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("monthly_budget_cents", sa.Integer(), nullable=True),
        sa.Column("default_max_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_project_settings_project_id", "project_settings", ["project_id"], unique=True)

    # ── api_keys ──────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(512), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("label", sa.String(128), server_default=sa.text("'Default'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # ── features ──────────────────────────────────────────────────────────
    op.create_table(
        "features",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("project_id", "slug", name="uq_project_feature_slug"),
    )
    op.create_index("ix_features_slug", "features", ["slug"])

    # ── feature_settings ──────────────────────────────────────────────────
    op.create_table(
        "feature_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feature_id", UUID(as_uuid=True), sa.ForeignKey("features.id", ondelete="CASCADE"), nullable=False),
        sa.Column("auto_mode", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("max_tokens_cap", sa.Integer(), nullable=True),
        sa.Column("preferred_model", sa.String(128), nullable=True),
        sa.Column("preferred_provider", sa.String(64), nullable=True),
        sa.Column("monthly_budget_cents", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_feature_settings_feature_id", "feature_settings", ["feature_id"], unique=True)

    # ── llm_requests (usage_logs) ─────────────────────────────────────────
    op.create_table(
        "llm_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_id", UUID(as_uuid=True), sa.ForeignKey("features.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_cents", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("estimated_savings_cents", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status_code", sa.Integer(), server_default=sa.text("200"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("was_rerouted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("original_model", sa.String(128), nullable=True),
        sa.Column("reroute_reason", sa.String(256), nullable=True),
        sa.Column("request_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_llm_requests_project_id", "llm_requests", ["project_id"])
    op.create_index("ix_llm_requests_feature_id", "llm_requests", ["feature_id"])
    op.create_index("ix_llm_requests_created_at", "llm_requests", ["created_at"])

    # ── feature_stats_daily ───────────────────────────────────────────────
    op.create_table(
        "feature_stats_daily",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("feature_id", UUID(as_uuid=True), sa.ForeignKey("features.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("total_requests", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_cost_cents", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("total_savings_cents", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("avg_latency_ms", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rerouted_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("top_models", sa.String(512), nullable=True),
        sa.UniqueConstraint("feature_id", "stat_date", name="uq_feature_date"),
    )
    op.create_index("ix_feature_stats_daily_stat_date", "feature_stats_daily", ["stat_date"])

    # ── project_monthly_usage ─────────────────────────────────────────────
    op.create_table(
        "project_monthly_usage",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("limit_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("project_id", "year_month", name="uq_project_month"),
    )

    # ── suggestions ───────────────────────────────────────────────────────
    op.create_table(
        "suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_id", UUID(as_uuid=True), sa.ForeignKey("features.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_savings_cents", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_suggestions_project_id", "suggestions", ["project_id"])

    # ── password_reset_tokens ─────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("password_reset_tokens")
    op.drop_table("suggestions")
    op.drop_table("project_monthly_usage")
    op.drop_table("feature_stats_daily")
    op.drop_table("llm_requests")
    op.drop_table("feature_settings")
    op.drop_table("features")
    op.drop_table("api_keys")
    op.drop_table("project_settings")
    op.drop_table("projects")
    op.drop_table("user_subscriptions")
    op.drop_table("plans")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
