"""Tests for normalization service."""

import pytest
from app.services.normalization import (
    normalize_phone, normalize_email, normalize_ip, normalize_upi,
    normalize_url, normalize_vehicle, normalize_device, normalize_entity_value,
)


class TestNormalizePhone:
    def test_with_country_code(self):
        assert normalize_phone("+91 98765 43210") == "9876543210"

    def test_with_zero_prefix(self):
        assert normalize_phone("09876543210") == "9876543210"

    def test_without_prefix(self):
        assert normalize_phone("9876543210") == "9876543210"

    def test_with_dashes(self):
        assert normalize_phone("+91-98765-43210") == "9876543210"

    def test_with_spaces_and_country_code(self):
        assert normalize_phone("+919876543210") == "9876543210"


class TestNormalizeEmail:
    def test_lowercase(self):
        assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_mixed_case(self):
        assert normalize_email("UsEr@ExAmPlE.cOm") == "user@example.com"


class TestNormalizeIP:
    def test_valid_ip(self):
        assert normalize_ip("192.168.1.1") == "192.168.1.1"

    def test_invalid_high_octet(self):
        assert normalize_ip("256.1.1.1") is None

    def test_invalid_letters(self):
        assert normalize_ip("abc.1.1.1") is None

    def test_valid_minimal(self):
        assert normalize_ip("0.0.0.0") == "0.0.0.0"


class TestNormalizeUPI:
    def test_uppercase(self):
        assert normalize_upi("USER@BANK") == "user@bank"

    def test_whitespace(self):
        assert normalize_upi(" user@bank ") == "user@bank"


class TestNormalizeURL:
    def test_trailing_slash(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/") == "https://example.com"

    def test_no_trailing_slash(self):
        assert normalize_url("https://example.com/path") == "https://example.com/path"


class TestNormalizeVehicle:
    def test_with_spaces(self):
        assert normalize_vehicle("MH 12 AB 1234") == "MH12AB1234"

    def test_with_dashes(self):
        assert normalize_vehicle("MH-12-AB-1234") == "MH12AB1234"

    def test_already_clean(self):
        assert normalize_vehicle("DL01AA1234") == "DL01AA1234"


class TestNormalizeDevice:
    def test_uppercase(self):
        assert normalize_device("imei-123456789012345") == "IMEI-123456789012345"

    def test_whitespace(self):
        assert normalize_device(" DEVICE-001 ") == "DEVICE-001"


class TestNormalizeEntityValue:
    def test_phone_routing(self):
        assert normalize_entity_value("PHONE", "+91 98765 43210") == "9876543210"

    def test_email_routing(self):
        assert normalize_entity_value("EMAIL", "TEST@X.COM") == "test@x.com"

    def test_ip_routing(self):
        assert normalize_entity_value("IP_ADDRESS", "10.0.0.1") == "10.0.0.1"

    def test_upi_routing(self):
        assert normalize_entity_value("UPI_ID", "USER@YBL") == "user@ybl"

    def test_person_fallback(self):
        result = normalize_entity_value("PERSON", "  Rahul Kumar  ")
        assert result == "rahul kumar"
