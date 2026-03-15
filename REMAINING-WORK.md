# AutoLLM — Remaining Work to Production

Last updated: March 15, 2026

---

## Status Summary

| Component | Status | Readiness |
|-----------|--------|-----------|
| Backend (FastAPI) | Complete | 90% |
| Database Models | Complete | 90% |
| Auth (JWT + Google OAuth) | Complete | 90% |
| Plan Enforcement | Complete | 95% |
| Cost Engine | Complete | 95% |
| Background Workers | Complete | 90% |
| TypeScript SDK | Complete | 95% |
| Docker Compose | Complete | 95% |
| Frontend (Next.js) | Complete | 90% |
| Testing | Not started | 0% |
| CI/CD | Not started | 0% |
| Documentation | Partial | 40% |

---

## CRITICAL — Must Fix Before Deployment

### ~~1. Frontend Restructure~~ ✅ DONE

The frontend has been fully restructured into a proper Next.js 14 App Router project with:
- `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`
- Root layout with AuthProvider + ProjectProvider
- Auth middleware for route protection
- Auth pages: `/login`, `/register`, `/callback` (OAuth)
- Dashboard layout with responsive Sidebar component
- 5 dashboard pages: Overview (charts), Features, Suggestions, Settings, Pricing
- 8 shared UI components: Card, Badge, Btn, StatCard, UsageBar, SuggIcon, Spinner, GoogleIcon
- AuthContext (login, register, logout, Google OAuth, refresh)
- ProjectContext (CRUD, current project selection)
- `useApiData` hook for data fetching with loading/error states
- All pages wired to real API client (`src/lib/api.ts`)
- Dockerfile for production container (standalone output)
- `.env.local.example`

---

### 1. Database Migrations (Alembic)

Currently the app uses `Base.metadata.create_all()` at startup, which is fine for development but dangerous in production (can't alter existing tables, no rollback).

**What's missing:**
- `backend/alembic.ini` — Alembic configuration
- `backend/alembic/env.py` — Migration environment setup
- `backend/alembic/versions/001_initial.py` — Initial schema migration
- Remove `create_all()` from `main.py` lifespan for production

**Work estimate:** 2-4 hours

---

### 3. Hardcoded Secrets

In `backend/app/config.py`:
```python
SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"  # MUST change
```

**Fix:** Generate a real secret with `openssl rand -hex 32` and load from environment variable. The config already reads from env vars, but the default is insecure.

**Work estimate:** 15 minutes

---

## HIGH PRIORITY — Should Fix Before Launch

### 4. Stripe Integration (Currently Stubbed)

In `backend/app/api/billing_routes.py`, the plan change endpoint has a comment:
```python
# TODO: Create Stripe checkout session / subscription
```

**What's needed:**
- Stripe Checkout session creation for upgrades
- Stripe webhook handler (`/api/webhooks/stripe`) for:
  - `checkout.session.completed` — activate subscription
  - `invoice.paid` — renew subscription
  - `invoice.payment_failed` — handle failed payment
  - `customer.subscription.deleted` — handle cancellation
- Stripe customer creation on user registration
- Subscription status sync

**Work estimate:** 1-2 days

---

### 5. Email Service

No email sending is implemented. Needed for:
- Email verification on registration
- Password reset flow
- Budget alert notifications (when suggestion engine detects overspend)
- Weekly usage digest (optional)

**Options:** Resend, SendGrid, AWS SES, Postmark

**Work estimate:** 4-6 hours

---

### 6. Rate Limiting

No rate limiting on any endpoints. The SDK ingest endpoint (`POST /api/sdk/ingest`) is especially vulnerable.

**What's needed:**
- Rate limiting middleware (e.g., `slowapi` or custom Redis-based)
- Per-API-key rate limits based on plan tier
- Global rate limits on auth endpoints (prevent brute force)

**Work estimate:** 2-4 hours

---

### ~~7. Frontend Dockerfile~~ ✅ DONE

Frontend Dockerfile created with multi-stage build (deps → builder → runner) using standalone output.

---

## MEDIUM PRIORITY — Before Public Launch

### 8. Testing

No test suite exists for any component.

**Backend tests needed:**
- `tests/test_auth.py` — Registration, login, token refresh, OAuth flow
- `tests/test_projects.py` — CRUD, API key generation, plan limits
- `tests/test_features.py` — CRUD, settings, auto mode permission
- `tests/test_ingest.py` — SDK logging, cost calculation, limit enforcement
- `tests/test_suggestions.py` — List, accept, dismiss
- `tests/test_billing.py` — Plan listing, plan change
- `tests/test_stats.py` — Overview and per-feature stats
- `tests/test_plan_service.py` — Plan enforcement edge cases
- `tests/test_cost_engine.py` — Cost calculation accuracy
- `tests/test_worker.py` — Aggregator and suggestion engine
- `tests/conftest.py` — Test database, fixtures, auth helpers

**SDK tests needed:**
- Config caching behavior
- Provider dispatch routing
- Auto mode rerouting logic
- Fail-open behavior when backend is down
- Fire-and-forget logging

**Work estimate:** 3-5 days

---

### 9. Input Validation Hardening

While Pydantic handles basic validation, there are gaps:
- No CSRF protection
- No input sanitization for string fields (XSS potential in feature names, project names)
- No file upload restrictions (if added later)
- Password strength validation is minimal (just length)

**Work estimate:** 4-6 hours

---

### 10. Logging & Observability

Currently uses basic Python logging. For production:
- Structured JSON logging (e.g., `structlog`)
- Request ID tracing across services
- Error tracking integration (Sentry)
- Metrics collection (Prometheus or DataDog)
- Health check endpoint (`/health` with DB + Redis connectivity)

**Work estimate:** 1 day

---

### 11. CORS Configuration

In `main.py`, CORS is configured with `allow_origins=["*"]` which is too permissive for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # CHANGE to actual frontend domain
)
```

**Work estimate:** 15 minutes

---

### 12. .gitignore

No `.gitignore` exists. Create one covering:
```
__pycache__/
*.pyc
.env
.env.local
node_modules/
dist/
.next/
*.egg-info/
.pytest_cache/
alembic/versions/__pycache__/
```

**Work estimate:** 10 minutes

---

## LOW PRIORITY — Nice to Have

### 13. SDK: npm Package Publishing
- Set up npm publish workflow
- Add README with usage examples
- Add JSDoc comments for IDE autocomplete
- Publish as `@autollm/sdk`

### 14. Landing Page / Marketing Site
- Public-facing landing page explaining AutoLLM
- Pricing page (public, not behind auth)
- Documentation site (API docs, SDK quickstart)

### 15. Admin Dashboard
- Internal admin panel for monitoring users, subscriptions, usage
- Feature flags system
- Ability to manually adjust plan limits

### 16. Multi-tenancy Improvements
- Team/organization support (multiple users per project)
- Role-based access control (owner, admin, member, viewer)
- Audit log for sensitive actions

### 17. Advanced SDK Features
- Batch logging (queue requests, flush periodically)
- Streaming support for LLM responses
- Request retry with exponential backoff
- Custom metadata tagging per request

### 18. CI/CD Pipeline
- GitHub Actions or similar for:
  - Run tests on PR
  - Lint + type check
  - Build Docker images
  - Deploy to staging on merge to `develop`
  - Deploy to production on merge to `main`

---

## Recommended Build Order

If picking this up for deployment, here's the most efficient order:

1. ~~**Frontend restructure**~~ ✅ DONE
2. ~~**Frontend Dockerfile**~~ ✅ DONE
3. ~~**.gitignore**~~ ✅ DONE
4. **Quick wins** (30 min): Fix CORS origins, fix SECRET_KEY, add `/health` endpoint
5. **Alembic migrations** (3 hours): Set up schema versioning
6. **Stripe integration** (1-2 days): Real billing flow
7. **Rate limiting** (3 hours): Protect the ingest endpoint
8. **Testing** (3-5 days): Backend + SDK test suites
9. **Email service** (4 hours): Verification + alerts
10. **Logging & monitoring** (1 day): Structured logs, Sentry, health checks
11. **CI/CD** (half day): Automated test + deploy pipeline

**Total estimated time to production-ready: ~1-2 weeks for a solo developer.**
