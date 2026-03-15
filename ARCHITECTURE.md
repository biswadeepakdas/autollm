# AutoLLM — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Customer's SaaS App                         │
│                                                                     │
│   import { AutoLLM } from '@autollm/sdk'                           │
│   const llm = new AutoLLM({ apiKey: 'allm_...' })                 │
│                                                                     │
│   const result = await llm.call({                                  │
│     feature: 'chat_support',                                       │
│     provider: 'openai',                                            │
│     model: 'gpt-4.1',                                             │
│     messages: [...],                                                │
│     providerApiKey: process.env.OPENAI_KEY                         │
│   })                                                                │
└──────────┬──────────────────────────────────┬───────────────────────┘
           │ 1. Fetch config                  │ 2. Call LLM
           │    GET /api/sdk/config            │    (directly)
           │                                   │
           │ 3. Log request                    ▼
           │    POST /api/sdk/ingest    ┌─────────────┐
           │                            │ LLM Provider │
           ▼                            │ (OpenAI,     │
┌─────────────────────┐                │  Anthropic,  │
│   AutoLLM Backend   │                │  Gemini,     │
│   (FastAPI)         │                │  NVIDIA NIM) │
│                     │                └─────────────┘
│  ┌──────────────┐   │
│  │ Auth Layer   │   │   Email + Password
│  │ (JWT + OAuth)│◄──┼── Google OAuth
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────┐   │
│  │ Plan Enforcer│   │   Checks: project limit,
│  │              │◄──┼── feature limit, request
│  │              │   │   quota, auto mode access
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────┐   │
│  │ API Routes   │   │   /projects, /features,
│  │              │   │   /ingest, /config,
│  │              │   │   /suggestions, /billing
│  └──────┬───────┘   │
│         │           │
│  ┌──────▼───────┐   │
│  │ Cost Engine  │   │   Pricing tables,
│  │              │   │   savings estimation,
│  │              │   │   auto mode routing
│  └──────────────┘   │
└──────────┬──────────┘
           │
     ┌─────▼─────┐     ┌────────────────────┐
     │ PostgreSQL │     │   Background Worker │
     │            │◄────┤                    │
     │ users      │     │  Aggregator (daily)│
     │ plans      │     │  Suggestion Engine │
     │ projects   │     │  (5 rules)         │
     │ features   │     └────────────────────┘
     │ llm_reqs   │
     │ stats      │     ┌────────────────────┐
     │ suggestions│     │   Frontend (React)  │
     └────────────┘     │                    │
           │            │  Auth screens      │
     ┌─────▼─────┐     │  Dashboard/Overview│
     │   Redis    │     │  Features page     │
     │ (queues)   │     │  Suggestions page  │
     └───────────┘     │  Settings page     │
                        │  Pricing page      │
                        └────────────────────┘
```

## Data Model

```
users
├── id (uuid, pk)
├── email (unique)
├── name
├── password_hash (nullable — null for OAuth-only)
├── is_active
└── timestamps

oauth_accounts
├── id (uuid, pk)
├── user_id → users.id
├── provider ("google", "github", etc.)
├── provider_user_id
├── provider_email
├── access_token, refresh_token
└── unique(provider, provider_user_id)

plans
├── id (uuid, pk)
├── name ("Free", "Pro", "Max")
├── code ("plan_free", "plan_pro", "plan_max")
├── monthly_request_limit
├── max_projects
├── max_features_per_project
├── auto_mode_enabled
├── price_monthly_cents
└── stripe_price_id

user_subscriptions
├── id (uuid, pk)
├── user_id → users.id (unique)
├── plan_id → plans.id
├── status (active, canceled, past_due)
├── stripe_subscription_id
└── period_start, period_end

projects
├── id (uuid, pk)
├── owner_id → users.id
├── name, slug
└── timestamps

api_keys
├── id (uuid, pk)
├── project_id → projects.id
├── key_hash (sha256)
├── key_prefix ("allm_xxxx")
├── label, is_active
└── timestamps

features
├── id (uuid, pk)
├── project_id → projects.id
├── name, slug
└── timestamps

feature_settings
├── feature_id → features.id (unique)
├── auto_mode, max_tokens_cap
├── preferred_model, preferred_provider
└── monthly_budget_cents

project_settings
├── project_id → projects.id (unique)
├── auto_mode_global
├── monthly_budget_cents
└── default_max_tokens

llm_requests
├── id (uuid, pk)
├── project_id → projects.id
├── feature_id → features.id
├── provider, model
├── prompt_tokens, completion_tokens, total_tokens
├── cost_cents, estimated_savings_cents
├── latency_ms, status_code, error
├── was_rerouted, original_model, reroute_reason
├── request_metadata (jsonb)
└── created_at (indexed)

feature_stats_daily
├── feature_id + stat_date (unique)
├── total_requests, tokens, cost, savings
├── avg_latency, errors, rerouted
└── top_models

project_monthly_usage
├── project_id + year_month (unique)
├── request_count
└── limit_hit_at

suggestions
├── id (uuid, pk)
├── project_id → projects.id
├── feature_id → features.id (nullable)
├── type (model_downgrade, token_cap, low_value_cut, provider_mix, budget_alert)
├── title, description
├── estimated_savings_cents, confidence
├── payload (jsonb)
├── status (pending, accepted, dismissed, auto_applied)
├── priority
└── timestamps
```

## Plan Enforcement Flow

```
Any resource-creating endpoint
         │
         ▼
   ┌───────────┐     ┌──────────────────────┐
   │ Auth layer │────►│ Get user's plan      │
   └───────────┘     │ (subscription → plan) │
                      └──────────┬───────────┘
                                 │
                      ┌──────────▼───────────┐
                      │ Check limit:         │
                      │ • Projects < max?    │
                      │ • Features < max?    │
                      │ • Requests < monthly?│
                      │ • Auto mode allowed? │
                      └──────────┬───────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              Within limit              Over limit
                    │                         │
                    ▼                         ▼
             Allow action            Return 403 with
                                     upsell message
```

## Auto Mode Rules (5 MVP Rules)

1. **Model Downgrade** — Features with avg prompt < 500 tokens → suggest cheaper model
2. **Token Cap** — Features where max completion > 3x avg → suggest p95 cap
3. **Low-Value Cut** — Features with >20% cost share but <5% usage → flag for review
4. **Provider Mix** — Cross-provider alternatives that save >$0.50/month → suggest
5. **Budget Alert** — Projected monthly spend > budget → alert with savings estimate

## Auth Flow

```
Email + Password:
  Register → hash password → create user → assign Free plan → JWT

Google OAuth:
  /auth/google → redirect to Google → callback → exchange code →
  check oauth_accounts → if linked: log in → if not: check users by email →
  if exists: link OAuth account → if not: create user + link → JWT

Both flows converge to same User model. Sessions via httpOnly cookies.
```

## SDK Behavior

```
1. SDK.call() invoked
2. Fetch config from /api/sdk/config (cached 60s)
3. If Auto mode ON for this feature:
   a. Check preferred_model override → reroute
   b. Apply max_tokens_cap
4. Call actual LLM provider directly (customer's API key)
5. Fire-and-forget: POST /api/sdk/ingest with usage data
6. If /ingest returns limit_exceeded → warn, don't break app
7. If backend is down → still call LLM, skip logging
```

## Future Hooks (Not Implemented Yet)

- `transparent_proxy` endpoint stub for direct HTTP proxy mode
- `cache_layer` interface in cost_engine for response caching
- `quality_evaluator` hook in suggestion engine for quality scoring
- `environment` field on projects for multi-env support
- `webhook_url` on project_settings for event notifications
