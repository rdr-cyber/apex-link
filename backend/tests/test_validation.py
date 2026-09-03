"""Tests for validation service."""

import pytest
from app.services.validation import (
    is_valid_phone, is_valid_email, is_valid_ip, is_valid_upi,
    is_valid_url, is_valid_vehicle, validate_entity,
)


class TestPhoneValidation:
    def test_valid_phone(self):
        assert is_valid_phone("9876543210") is True

    def test_starts_with_6(self):
        assert is_valid_phone("6123456789") is True

    def test_starts_with_5(self):
        assert is_valid_phone("5123456789") is False

    def test_too_short(self):
        assert is_valid_phone("12345") is False

    def test_too_long(self):
        assert is_valid_phone("12345678901") is False


class TestEmailValidation:
    def test_valid(self):
        assert is_valid_email("user@example.com") is True

    def test_no_at(self):
        assert is_valid_email("userexample.com") is False

    def test_no_domain_dot(self):
        assert is_valid_email("user@localhost") is False

    def test_empty(self):
        assert is_valid_email("") is False


class TestIPValidation:
    def test_valid(self):
        assert is_valid_ip("192.168.1.1") is True

    def test_invalid(self):
        assert is_valid_ip("999.1.1.1") is False


class TestUPIValidation:
    def test_valid(self):
        assert is_valid_upi("user@ybl") is True

    def test_no_at(self):
        assert is_valid_upi("userybl") is False

    def test_empty_provider(self):
        assert is_valid_upi("user@") is False

    def test_numeric_provider(self):
        assert is_valid_upi("user@123") is False


class TestURLValidation:
    def test_https(self):
        assert is_valid_url("https://example.com") is True

    def test_http(self):
        assert is_valid_url("http://example.com") is True

    def test_no_scheme(self):
        assert is_valid_url("example.com") is False


class TestVehicleValidation:
    def test_valid(self):
        assert is_valid_vehicle("WB12AB1234") is True

    def test_invalid(self):
        assert is_valid_vehicle("12345") is False

    def test_valid_dl(self):
        assert is_valid_vehicle("DL01AA1234") is True


class TestValidateEntity:
    def test_valid_phone(self):
        ok, _ = validate_entity("PHONE", "9876543210")
        assert ok is True

    def test_invalid_phone(self):
        ok, reason = validate_entity("PHONE", "12345")
        assert ok is False
        assert "mobile" in reason.lower()

    def test_valid_email(self):
        ok, _ = validate_entity("EMAIL", "test@example.com")
        assert ok is True

    def test_valid_ip(self):
        ok, _ = validate_entity("IP_ADDRESS", "10.0.0.1")
        assert ok is True

    def test_valid_upi(self):
        ok, _ = validate_entity("UPI_ID", "user@ybl")
        assert ok is True

    def test_person_nonempty(self):
        ok, _ = validate_entity("PERSON", "rahul kumar")
        assert ok is True

    def test_person_empty(self):
        ok, _ = validate_entity("PERSON", "")
        assert ok is False
