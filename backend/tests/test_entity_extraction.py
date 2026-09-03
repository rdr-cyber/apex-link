"""Entity extraction and normalization tests."""

import pytest
from app.services.entity_extraction import extract_entities_from_text
from app.services.normalization import (
    normalize_phone,
    normalize_email,
    normalize_ip,
    normalize_upi,
    normalize_vehicle,
)
from app.services.entity_resolution import (
    is_deterministic_match,
    compute_name_similarity,
    should_merge_entities,
)


class TestPhoneNormalization:
    def test_indian_phone_with_country_code(self):
        assert normalize_phone("+91 98765 43210") == "9876543210"

    def test_indian_phone_with_zero(self):
        assert normalize_phone("09876543210") == "9876543210"

    def test_indian_phone_without_prefix(self):
        assert normalize_phone("9876543210") == "9876543210"

    def test_indian_phone_with_dashes(self):
        assert normalize_phone("+91-98765-43210") == "9876543210"


class TestEmailNormalization:
    def test_lowercase(self):
        assert normalize_email("Test@Example.COM") == "test@example.com"

    def test_whitespace(self):
        assert normalize_email("  user@domain.com  ") == "user@domain.com"


class TestIPNormalization:
    def test_valid_ip(self):
        assert normalize_ip("192.168.1.1") == "192.168.1.1"

    def test_invalid_ip_high_octet(self):
        assert normalize_ip("256.1.1.1") is None

    def test_invalid_ip_letters(self):
        assert normalize_ip("abc.1.1.1") is None


class TestUPINormalization:
    def test_uppercase(self):
        assert normalize_upi("USER@BANK") == "user@bank"

    def test_whitespace(self):
        assert normalize_upi(" user@bank ") == "user@bank"


class TestVehicleNormalization:
    def test_with_spaces(self):
        assert normalize_vehicle("MH 12 AB 1234") == "MH12AB1234"

    def test_with_dashes(self):
        assert normalize_vehicle("MH-12-AB-1234") == "MH12AB1234"


class TestExtraction:
    def test_phone_extraction(self):
        text = "Call Vikram at +91 98765 43210 for details"
        entities = extract_entities_from_text(text)
        phones = [e for e in entities if e.entity_type == "PHONE"]
        assert len(phones) >= 1
        assert phones[0].normalized_value == "9876543210"

    def test_email_extraction(self):
        text = "Contact at vikram.p@demo-mail.com"
        entities = extract_entities_from_text(text)
        emails = [e for e in entities if e.entity_type == "EMAIL"]
        assert len(emails) >= 1
        assert emails[0].normalized_value == "vikram.p@demo-mail.com"

    def test_ip_extraction(self):
        text = "Server IP: 192.168.1.105"
        entities = extract_entities_from_text(text)
        ips = [e for e in entities if e.entity_type == "IP_ADDRESS"]
        assert len(ips) >= 1
        assert ips[0].normalized_value == "192.168.1.105"

    def test_upi_extraction(self):
        text = "Payment to vikram.p@upibank"
        entities = extract_entities_from_text(text)
        upis = [e for e in entities if e.entity_type == "UPI_ID"]
        assert len(upis) >= 1
        assert upis[0].normalized_value == "vikram.p@upibank"

    def test_invalid_ip_rejected(self):
        text = "Invalid IP: 999.999.999.999"
        entities = extract_entities_from_text(text)
        ips = [e for e in entities if e.entity_type == "IP_ADDRESS"]
        assert len(ips) == 0

    def test_deduplication(self):
        text = "Phone 9876543210 and also +91 98765 43210"
        entities = extract_entities_from_text(text)
        phones = [e for e in entities if e.entity_type == "PHONE"]
        assert len(phones) == 1

    def test_multiple_entity_types(self):
        text = """
        Contact Vikram at +91 98765 43210 or vikram.p@demo-mail.com
        IP logged: 192.168.1.105. UPI: vikram.p@upibank
        Vehicle MH 12 AB 1234 spotted nearby.
        """
        entities = extract_entities_from_text(text)
        types = {e.entity_type for e in entities}
        assert "PHONE" in types
        assert "EMAIL" in types
        assert "IP_ADDRESS" in types
        assert "UPI_ID" in types
        assert "VEHICLE" in types


class TestEntityResolution:
    def test_deterministic_phone_match(self):
        assert is_deterministic_match("PHONE", "9876543210", "9876543210") is True

    def test_deterministic_phone_no_match(self):
        assert is_deterministic_match("PHONE", "9876543210", "8765432109") is False

    def test_deterministic_email_match(self):
        assert is_deterministic_match("EMAIL", "test@example.com", "test@example.com") is True

    def test_name_similarity_exact(self):
        assert compute_name_similarity("Rahul Kumar", "Rahul Kumar") == 1.0

    def test_name_similarity_similar(self):
        sim = compute_name_similarity("Rahul Kumar", "Rahul K.")
        assert sim > 0.8

    def test_name_similarity_different(self):
        sim = compute_name_similarity("Rahul Kumar", "Priya Singh")
        assert sim < 0.5

    def test_should_merge_deterministic(self):
        merge, confidence = should_merge_entities("PHONE", "9876543210", "9876543210")
        assert merge is True
        assert confidence == 1.0

    def test_should_not_merge_different_phones(self):
        merge, _ = should_merge_entities("PHONE", "9876543210", "8765432109")
        assert merge is False

    def test_should_merge_similar_names(self):
        merge, confidence = should_merge_entities("PERSON", "rahul kumar", "rahul k.")
        assert merge is True
        assert confidence > 0.7

    def test_should_not_merge_different_names(self):
        merge, _ = should_merge_entities("PERSON", "rahul kumar", "priya singh")
        assert merge is False
