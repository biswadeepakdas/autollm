"""Authentication routes — email/password + Google OAuth."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.database import get_db
from app.config import settings
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token, create_refresh_token, decode_token
from app.auth.deps import get_current_user, CurrentUser
from app.models.user import User, OAuthAccount
from app.models.plan import Plan, PlanCode, UserSubscription
from app.api.schemas import (
    RegisterRequest, LoginRequest, AuthResponse, UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_response(user: User) -> UserResponse:
    plan_name = None
    plan_code = None
    if user.subscription and user.subscription.plan:
        plan_name = user.subscription.plan.name
        plan_code = user.subscription.plan.code
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plan_name=plan_name,
        plan_code=plan_code,
        created_at=user.created_at,
    )


async def _assign_free_plan(db: AsyncSession, user: User) -> None:
    """Give a new user the Free plan."""
    result = await db.execute(select(Plan).where(Plan.code == PlanCode.FREE.value))
    free_plan = result.scalar_one_or_none()
    if free_plan:
        sub = UserSubscription(user_id=user.id, plan_id=free_plan.id, status="active")
        db.add(sub)
        await db.flush()
        # Reload subscription
        result = await db.execute(
            select(User).options(selectinload(User.subscription).selectinload(UserSubscription.plan)).where(User.id == user.id)
        )
        return result.scalar_one()
    return user


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, samesite="lax", max_age=3600, secure=False)
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax", max_age=86400 * 30, secure=False)


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    user = await _assign_free_plan(db, user)

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_response(user))


# ── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.subscription).selectinload(UserSubscription.plan)).where(User.email == body.email)
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_response(user))


# ── Refresh ──────────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(
        select(User).options(selectinload(User.subscription).selectinload(UserSubscription.plan)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access = create_access_token(user.id, user.email)
    _set_auth_cookies(response, access, token)
    return {"access_token": access}


# ── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


# ── Me ───────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return _user_response(user)


# ── Google OAuth ─────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login():
    """Return the Google OAuth consent URL."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {"url": url}


@router.get("/google/callback")
async def google_callback(code: str, response: Response, db: AsyncSession = Depends(get_db)):
    """Exchange Google auth code for tokens, create/login user."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code with Google")
        tokens = token_resp.json()

        # Get user info
        info_resp = await client.get(GOOGLE_USERINFO_URL, headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        })
        if info_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Google user info")
        google_user = info_resp.json()

    google_id = google_user["id"]
    google_email = google_user.get("email")
    google_name = google_user.get("name")

    # Check if OAuth account already linked
    result = await db.execute(
        select(OAuthAccount).where(OAuthAccount.provider == "google", OAuthAccount.provider_user_id == google_id)
    )
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # Existing OAuth link → log in
        result = await db.execute(
            select(User).options(selectinload(User.subscription).selectinload(UserSubscription.plan)).where(User.id == oauth_account.user_id)
        )
        user = result.scalar_one()
    else:
        # Check if user exists by email
        result = await db.execute(
            select(User).options(selectinload(User.subscription).selectinload(UserSubscription.plan)).where(User.email == google_email)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(email=google_email, name=google_name)
            db.add(user)
            await db.flush()
            user = await _assign_free_plan(db, user)

        # Link OAuth account
        oauth = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_id,
            provider_email=google_email,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
        )
        db.add(oauth)
        await db.flush()

    access = create_access_token(user.id, user.email)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)

    # Redirect to frontend dashboard
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard?auth=success", status_code=302)


# ── Connect OAuth (link account in settings) ─────────────────────────────────

@router.post("/connect/google")
async def connect_google(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Return URL for linking Google to an existing account."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    # Check if already connected
    result = await db.execute(
        select(OAuthAccount).where(OAuthAccount.user_id == user.id, OAuthAccount.provider == "google")
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Google account already connected")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": f"connect:{user.id}",
    }
    url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return {"url": url}
