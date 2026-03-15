"""Email service — sends transactional emails via SendGrid or logs in dev."""

import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_content: str) -> bool:
    """Send an email. Uses SendGrid in production, logs in development."""
    if not settings.SENDGRID_API_KEY:
        logger.info(f"[EMAIL-DEV] To: {to} | Subject: {subject}")
        logger.debug(f"[EMAIL-DEV] Body: {html_content[:200]}...")
        return True

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": settings.EMAIL_FROM, "name": settings.EMAIL_FROM_NAME},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_content}],
                },
            )
            if response.status_code in (200, 201, 202):
                logger.info(f"Email sent to {to}: {subject}")
                return True
            else:
                logger.error(f"SendGrid error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


async def send_password_reset_email(to: str, reset_url: str) -> bool:
    """Send password reset email."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6366f1;">Reset Your Password</h2>
        <p>You requested a password reset for your AutoLLM account.</p>
        <p>Click the button below to reset your password. This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <a href="{reset_url}" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
            Reset Password
        </a>
        <p style="color: #666; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px;">AutoLLM — LLM Cost Optimization Platform</p>
    </div>
    """
    return await send_email(to, "Reset Your Password — AutoLLM", html)


async def send_welcome_email(to: str, name: Optional[str] = None) -> bool:
    """Send welcome email after registration."""
    display_name = name or "there"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6366f1;">Welcome to AutoLLM!</h2>
        <p>Hi {display_name},</p>
        <p>Thanks for signing up! AutoLLM helps you monitor and optimize your LLM costs across all providers.</p>
        <h3>Getting Started:</h3>
        <ol>
            <li>Create a project in your dashboard</li>
            <li>Generate an API key</li>
            <li>Install our SDK: <code>npm install @autollm/sdk</code></li>
            <li>Start tracking your LLM usage</li>
        </ol>
        <a href="{settings.FRONTEND_URL}/dashboard" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 16px 0;">
            Go to Dashboard
        </a>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #999; font-size: 12px;">AutoLLM — LLM Cost Optimization Platform</p>
    </div>
    """
    return await send_email(to, "Welcome to AutoLLM!", html)
