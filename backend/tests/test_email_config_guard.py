"""Tests for email provider production configuration guard."""

import pytest
from unittest.mock import patch


def test_console_provider_rejected_in_production():
    """EMAIL_PROVIDER=console must be rejected when DEBUG=False."""
    from app.services.email_provider import get_email_provider, ConfigurationError

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.EMAIL_PROVIDER = "console"

        with pytest.raises(ConfigurationError, match="not allowed in production"):
            get_email_provider()


def test_console_provider_allowed_in_development():
    """EMAIL_PROVIDER=console must be allowed when DEBUG=True."""
    from app.services.email_provider import get_email_provider, ConsoleEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = True
        mock_settings.return_value.EMAIL_PROVIDER = "console"

        provider = get_email_provider()
        assert isinstance(provider, ConsoleEmailProvider)


def test_smtp_provider_rejected_without_host_in_production():
    """EMAIL_PROVIDER=smtp without SMTP_HOST must be rejected in production."""
    from app.services.email_provider import get_email_provider, ConfigurationError

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.EMAIL_PROVIDER = "smtp"
        mock_settings.return_value.SMTP_HOST = ""

        with pytest.raises(ConfigurationError, match="requires SMTP_HOST"):
            get_email_provider()


def test_smtp_provider_allowed_with_host_in_production():
    """EMAIL_PROVIDER=smtp with SMTP_HOST must be allowed in production."""
    from app.services.email_provider import get_email_provider, SMTPEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.EMAIL_PROVIDER = "smtp"
        mock_settings.return_value.SMTP_HOST = "smtp.example.com"

        provider = get_email_provider()
        assert isinstance(provider, SMTPEmailProvider)


def test_smtp_provider_allowed_in_development():
    """EMAIL_PROVIDER=smtp must be allowed in development mode."""
    from app.services.email_provider import get_email_provider, SMTPEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = True
        mock_settings.return_value.EMAIL_PROVIDER = "smtp"
        mock_settings.return_value.SMTP_HOST = ""  # Even without host, dev mode allows it

        provider = get_email_provider()
        assert isinstance(provider, SMTPEmailProvider)


def test_unknown_provider_rejected():
    """Unknown EMAIL_PROVIDER value must be rejected."""
    from app.services.email_provider import get_email_provider, ConfigurationError

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.EMAIL_PROVIDER = "carrier_pigeon"

        with pytest.raises(ConfigurationError, match="Unknown EMAIL_PROVIDER"):
            get_email_provider()


def test_mock_provider_rejected_in_production():
    """EMAIL_PROVIDER=mock must be rejected in production."""
    from app.services.email_provider import get_email_provider, ConfigurationError

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.EMAIL_PROVIDER = "mock"

        with pytest.raises(ConfigurationError, match="not allowed in production"):
            get_email_provider()


def test_mock_provider_allowed_in_development():
    """EMAIL_PROVIDER=mock must be allowed in development."""
    from app.services.email_provider import get_email_provider, ConsoleEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = True
        mock_settings.return_value.EMAIL_PROVIDER = "mock"

        provider = get_email_provider()
        assert isinstance(provider, ConsoleEmailProvider)


def test_demo_provider_allowed_in_production():
    """EMAIL_PROVIDER=demo must be allowed in production (DEBUG=False)."""
    from app.services.email_provider import get_email_provider, DemoEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.EMAIL_PROVIDER = "demo"

        provider = get_email_provider()
        assert isinstance(provider, DemoEmailProvider)


def test_demo_provider_allowed_in_development():
    """EMAIL_PROVIDER=demo must be allowed in development (DEBUG=True)."""
    from app.services.email_provider import get_email_provider, DemoEmailProvider

    with patch("app.core.settings.get_settings") as mock_settings:
        mock_settings.return_value.DEBUG = True
        mock_settings.return_value.EMAIL_PROVIDER = "demo"

        provider = get_email_provider()
        assert isinstance(provider, DemoEmailProvider)


class TestProductionSecretValidation:
    """Verify production rejects weak JWT secrets."""

    def test_weak_secret_rejected_in_production(self):
        """Production must reject obviously weak SECRET_KEY values."""
        import os
        # Ensure DEBUG is false for production check
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=False):
            from app.core.settings import Settings
            with pytest.raises(ValueError, match="insecure"):
                Settings(
                    SECRET_KEY="CHANGE_ME_BEFORE_PRODUCTION",
                    DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
                    DATABASE_URL_SYNC="postgresql+psycopg2://test:test@localhost/test",
                )

    def test_strong_secret_accepted_in_production(self):
        """Production must accept a strong SECRET_KEY."""
        import os
        strong_key = "a" * 64  # 64-char hex string
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=False):
            from app.core.settings import Settings
            s = Settings(
                SECRET_KEY=strong_key,
                DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
                DATABASE_URL_SYNC="postgresql+psycopg2://test:test@localhost/test",
            )
            assert s.SECRET_KEY == strong_key
