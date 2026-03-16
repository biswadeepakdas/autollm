"""Password reset routes — forgot + reset password flow."""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta


def _utcnow():
    """Return current UTC time, timezone-aware."""
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    """Make a naive datetime UTC-aware (for SQLite compatibility in tests)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.auth.passwords import hash_password
from app.services.email_service import send_password_reset_email
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class VerifyTokenRequest(BaseModel):
    token: str


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password reset email if the user exists."""
    # Always return success to prevent email enumeration
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user and user.password_hash:
        # Invalidate existing reset tokens for this user
        existing = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,
            )
        )
        for token in existing.scalars().all():
            token.used = True

        # Generate new token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.flush()

        # Send email
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        await send_password_reset_email(user.email, reset_url)

    return {"ok": True, "message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a valid token."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if _ensure_aware(reset_token.expires_at) < _utcnow():
        reset_token.used = True
        raise HTTPException(status_code=400, detail="Reset token has expired")

    # Update password
    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    reset_token.used = True

    return {"ok": True, "message": "Password has been reset. You can now log in."}


@router.post("/verify-reset-token")
async def verify_reset_token(body: VerifyTokenRequest, db: AsyncSession = Depends(get_db)):
    """Check if a reset token is still valid."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token or _ensure_aware(reset_token.expires_at) < _utcnow():
        return {"valid": False}

    return {"valid": True}
