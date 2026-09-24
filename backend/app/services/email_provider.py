"""Email provider abstraction for APEX LINK.

Provides a common interface for sending emails, with implementations
for development (console output) and production (SMTP).

Usage:
    provider = get_email_provider()
    await provider.send_verification_email(email, token, expires_at)
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailProvider(Protocol):
    """Abstract email provider interface."""

    async def send_verification_email(
        self, to_email: str, token: str, expires_at: datetime
    ) -> bool:
        """Send a verification email. Returns True on success."""
        ...


class ConsoleEmailProvider:
    """Development-only provider that prints emails to stdout/log.

    NEVER use in production. The raw verification token is displayed
    explicitly for development convenience.
    """

    async def send_verification_email(
        self, to_email: str, token: str, expires_at: datetime
    ) -> bool:
        from app.core.settings import get_settings
        settings = get_settings()
        base_url = settings.FRONTEND_BASE_URL
        verification_url = f"{base_url}/verify-email?token={token}"

        message = f"""
{'=' * 60}
APEX LINK EMAIL VERIFICATION
{'=' * 60}
Recipient: {to_email}
Verification URL: {verification_url}
Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
{'=' * 60}
NOTE: This is the ConsoleEmailProvider (development only).
Raw token: {token}
{'=' * 60}
"""
        print(message)
        logger.info("Verification email (console) sent to %s", to_email)
        return True


class SMTPEmailProvider:
    """Production SMTP email provider.

    Configuration via environment variables:
        SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM
    """

    async def send_verification_email(
        self, to_email: str, token: str, expires_at: datetime
    ) -> bool:
        from app.core.settings import get_settings
        import smtplib
        from email.mime.text import MIMEText

        settings = get_settings()
        base_url = settings.FRONTEND_BASE_URL
        verification_url = f"{base_url}/verify-email?token={token}"

        msg = MIMEText(
            f"You requested email verification for APEX LINK.\n\n"
            f"Please verify your email by clicking the link below:\n\n"
            f"{verification_url}\n\n"
            f"This link expires at {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}.\n\n"
            f"If you did not request this verification, please ignore this email.\n",
            "plain",
        )
        msg["Subject"] = "APEX LINK — Verify Your Email"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USERNAME:
                    server.starttls()
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Verification email (SMTP) sent to %s", to_email)
            return True
        except Exception:
            logger.exception("Failed to send verification email via SMTP to %s", to_email)
            return False


class ConfigurationError(Exception):
    """Raised when the application is misconfigured for its deployment mode."""
    pass


class DemoEmailProvider:
    """Demo/public deployment provider.

    CRITICAL SECURITY: This provider NEVER logs, prints, or exposes
    the raw verification token. It only logs that a verification was
    requested for a given email address.

    In the standard demo deployment, all seeded accounts are
    pre-verified (email_verified=True). This provider exists so
    that the email verification flow does not crash in production
    when EMAIL_PROVIDER=demo is set.
    """

    async def send_verification_email(
        self, to_email: str, token: str, expires_at: datetime
    ) -> bool:
        # SECURITY: Never log, print, or expose the raw token.
        # Never include the token in any URL, message, or output.
        # Only log that a verification was requested.
        logger.info(
            "[DEMO] Verification email requested for %s (token expires %s). "
            "Raw token is NOT logged for security.",
            to_email,
            expires_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        )
        return True


def get_email_provider() -> EmailProvider:
    """Factory that returns the configured email provider.

    Production guard:
    - EMAIL_PROVIDER=console is rejected when DEBUG=False
    - EMAIL_PROVIDER=smtp requires valid SMTP configuration
    - EMAIL_PROVIDER=demo is allowed in production (logs tokens server-side)
    """
    from app.core.settings import get_settings
    settings = get_settings()

    provider_type = settings.EMAIL_PROVIDER.lower()
    is_production = not settings.DEBUG

    if provider_type == "console":
        if is_production:
            raise ConfigurationError(
                "EMAIL_PROVIDER=console is not allowed in production (DEBUG=False). "
                "Use EMAIL_PROVIDER=smtp for real email, or EMAIL_PROVIDER=demo for demo deployments."
            )
        return ConsoleEmailProvider()

    elif provider_type == "demo":
        # Allowed in both dev and production — logs tokens server-side
        return DemoEmailProvider()

    elif provider_type == "smtp":
        if is_production and not settings.SMTP_HOST:
            raise ConfigurationError(
                "EMAIL_PROVIDER=smtp requires SMTP_HOST to be configured."
            )
        return SMTPEmailProvider()

    elif provider_type == "mock":
        if is_production:
            raise ConfigurationError(
                "EMAIL_PROVIDER=mock is not allowed in production (DEBUG=False)."
            )
        return ConsoleEmailProvider()

    else:
        raise ConfigurationError(
            f"Unknown EMAIL_PROVIDER: '{provider_type}'. "
            "Valid options: console, demo, smtp, mock."
        )
