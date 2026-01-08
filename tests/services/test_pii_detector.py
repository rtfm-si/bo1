"""Tests for PII detection service.

Tests cover:
- Email detection
- SSN detection
- Phone number detection
- Credit card detection
- IP address detection
- Name detection (heuristic)
- Address detection (heuristic)
- Date of birth detection
- False positive mitigation
- Sampling behavior
- Confidence scoring
"""

import pandas as pd

from backend.services.pii_detector import (
    PiiType,
    _mask_value,
    detect_pii_columns,
    detect_pii_in_csv,
)


class TestEmailDetection:
    """Tests for email address detection."""

    def test_detects_email_column(self):
        """Should detect column with email addresses."""
        df = pd.DataFrame(
            {
                "email": [
                    "john@example.com",
                    "jane.doe@company.org",
                    "user123@mail.co.uk",
                    "test@test.com",
                    "another@email.net",
                ],
                "name": ["John", "Jane", "User", "Test", "Another"],
            }
        )

        warnings = detect_pii_columns(df)

        email_warnings = [w for w in warnings if w.pii_type == PiiType.EMAIL]
        assert len(email_warnings) == 1
        assert email_warnings[0].column_name == "email"
        assert email_warnings[0].confidence >= 0.5

    def test_ignores_non_email_column(self):
        """Should not flag column without emails."""
        df = pd.DataFrame(
            {
                "product_code": ["ABC123", "DEF456", "GHI789", "JKL012", "MNO345"],
            }
        )

        warnings = detect_pii_columns(df)

        email_warnings = [w for w in warnings if w.pii_type == PiiType.EMAIL]
        assert len(email_warnings) == 0


class TestSsnDetection:
    """Tests for Social Security Number detection."""

    def test_detects_ssn_with_dashes(self):
        """Should detect SSN format XXX-XX-XXXX."""
        df = pd.DataFrame(
            {
                "ssn": [
                    "123-45-6789",
                    "234-56-7890",
                    "345-67-8901",
                    "456-78-9012",
                    "567-89-0123",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        ssn_warnings = [w for w in warnings if w.pii_type == PiiType.SSN]
        assert len(ssn_warnings) == 1
        assert ssn_warnings[0].column_name == "ssn"

    def test_detects_ssn_without_dashes(self):
        """Should detect SSN format XXXXXXXXX."""
        df = pd.DataFrame(
            {
                "tax_id": [
                    "123456789",
                    "234567890",
                    "345678901",
                    "456789012",
                    "567890123",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        ssn_warnings = [w for w in warnings if w.pii_type == PiiType.SSN]
        assert len(ssn_warnings) == 1

    def test_avoids_product_code_false_positive(self):
        """Should not flag product codes that happen to be 9 digits."""
        # Product codes with letters mixed in shouldn't match
        df = pd.DataFrame(
            {
                "sku": ["SKU123456", "PRD789012", "ITM345678", "BOX901234", "PKG567890"],
            }
        )

        warnings = detect_pii_columns(df)

        ssn_warnings = [w for w in warnings if w.pii_type == PiiType.SSN]
        assert len(ssn_warnings) == 0


class TestPhoneDetection:
    """Tests for phone number detection."""

    def test_detects_phone_with_dashes(self):
        """Should detect phone format XXX-XXX-XXXX."""
        df = pd.DataFrame(
            {
                "phone": [
                    "123-456-7890",
                    "234-567-8901",
                    "345-678-9012",
                    "456-789-0123",
                    "567-890-1234",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        phone_warnings = [w for w in warnings if w.pii_type == PiiType.PHONE]
        assert len(phone_warnings) == 1

    def test_detects_phone_with_parentheses(self):
        """Should detect phone format (XXX) XXX-XXXX."""
        df = pd.DataFrame(
            {
                "mobile": [
                    "(123) 456-7890",
                    "(234) 567-8901",
                    "(345) 678-9012",
                    "(456) 789-0123",
                    "(567) 890-1234",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        phone_warnings = [w for w in warnings if w.pii_type == PiiType.PHONE]
        assert len(phone_warnings) == 1

    def test_detects_phone_with_country_code(self):
        """Should detect phone format +1-XXX-XXX-XXXX."""
        df = pd.DataFrame(
            {
                "tel": [
                    "+1-123-456-7890",
                    "+1-234-567-8901",
                    "+1-345-678-9012",
                    "+1-456-789-0123",
                    "+1-567-890-1234",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        phone_warnings = [w for w in warnings if w.pii_type == PiiType.PHONE]
        assert len(phone_warnings) == 1


class TestCreditCardDetection:
    """Tests for credit card number detection."""

    def test_detects_credit_card_with_spaces(self):
        """Should detect credit card format XXXX XXXX XXXX XXXX."""
        df = pd.DataFrame(
            {
                "card": [
                    "4111 1111 1111 1111",
                    "5500 0000 0000 0004",
                    "3400 0000 0000 009",
                    "6011 0000 0000 0004",
                    "3530 1113 3330 0000",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        cc_warnings = [w for w in warnings if w.pii_type == PiiType.CREDIT_CARD]
        assert len(cc_warnings) == 1

    def test_detects_credit_card_with_dashes(self):
        """Should detect credit card format XXXX-XXXX-XXXX-XXXX."""
        df = pd.DataFrame(
            {
                "payment": [
                    "4111-1111-1111-1111",
                    "5500-0000-0000-0004",
                    "3400-0000-0000-009",
                    "6011-0000-0000-0004",
                    "3530-1113-3330-0000",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        cc_warnings = [w for w in warnings if w.pii_type == PiiType.CREDIT_CARD]
        assert len(cc_warnings) == 1


class TestIpAddressDetection:
    """Tests for IP address detection."""

    def test_detects_ipv4_addresses(self):
        """Should detect IPv4 addresses."""
        df = pd.DataFrame(
            {
                "client_ip": [
                    "192.168.1.1",
                    "10.0.0.1",
                    "172.16.0.1",
                    "8.8.8.8",
                    "1.1.1.1",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        ip_warnings = [w for w in warnings if w.pii_type == PiiType.IP_ADDRESS]
        assert len(ip_warnings) == 1

    def test_ignores_invalid_ip(self):
        """Should not flag invalid IP addresses."""
        df = pd.DataFrame(
            {
                "data": [
                    "999.999.999.999",  # Invalid octets
                    "1.2.3",  # Too few octets
                    "not.an.ip.addr",
                    "12345",
                    "random",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        ip_warnings = [w for w in warnings if w.pii_type == PiiType.IP_ADDRESS]
        assert len(ip_warnings) == 0


class TestDateOfBirthDetection:
    """Tests for date of birth detection."""

    def test_detects_dob_mm_dd_yyyy(self):
        """Should detect DOB format MM/DD/YYYY."""
        df = pd.DataFrame(
            {
                "dob": [
                    "01/15/1990",
                    "12/25/1985",
                    "06/30/2000",
                    "03/01/1975",
                    "09/22/1988",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        dob_warnings = [w for w in warnings if w.pii_type == PiiType.DATE_OF_BIRTH]
        assert len(dob_warnings) == 1

    def test_detects_dob_yyyy_mm_dd(self):
        """Should detect DOB format YYYY-MM-DD."""
        df = pd.DataFrame(
            {
                "birthday": [
                    "1990-01-15",
                    "1985-12-25",
                    "2000-06-30",
                    "1975-03-01",
                    "1988-09-22",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        dob_warnings = [w for w in warnings if w.pii_type == PiiType.DATE_OF_BIRTH]
        assert len(dob_warnings) == 1


class TestNameDetection:
    """Tests for name detection (heuristic-based)."""

    def test_detects_first_name_column(self):
        """Should detect column named 'first_name' with name-like values."""
        df = pd.DataFrame(
            {
                "first_name": [
                    "John",
                    "Jane",
                    "Michael",
                    "Sarah",
                    "David",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        name_warnings = [w for w in warnings if w.pii_type == PiiType.NAME]
        assert len(name_warnings) == 1

    def test_detects_full_name_column(self):
        """Should detect column named 'full_name' with name-like values."""
        df = pd.DataFrame(
            {
                "full_name": [
                    "John Smith",
                    "Jane Doe",
                    "Michael Johnson",
                    "Sarah Williams",
                    "David Brown",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        name_warnings = [w for w in warnings if w.pii_type == PiiType.NAME]
        assert len(name_warnings) == 1


class TestAddressDetection:
    """Tests for address detection (heuristic-based)."""

    def test_detects_street_address_column(self):
        """Should detect column with street addresses."""
        df = pd.DataFrame(
            {
                "address": [
                    "123 Main St",
                    "456 Oak Avenue",
                    "789 Elm Road",
                    "321 Pine Blvd",
                    "654 Cedar Lane",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        addr_warnings = [w for w in warnings if w.pii_type == PiiType.ADDRESS]
        assert len(addr_warnings) == 1

    def test_detects_zip_code_in_address(self):
        """Should detect addresses containing zip codes."""
        df = pd.DataFrame(
            {
                "street": [
                    "New York, NY 10001",
                    "Los Angeles, CA 90001",
                    "Chicago, IL 60601",
                    "Houston, TX 77001",
                    "Phoenix, AZ 85001",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        addr_warnings = [w for w in warnings if w.pii_type == PiiType.ADDRESS]
        assert len(addr_warnings) == 1


class TestConfidenceScoring:
    """Tests for confidence scoring."""

    def test_high_match_ratio_increases_confidence(self):
        """Higher match ratio should increase confidence."""
        df = pd.DataFrame(
            {
                "email": [f"user{i}@example.com" for i in range(100)],  # 100% match
            }
        )

        warnings = detect_pii_columns(df)

        assert len(warnings) == 1
        assert warnings[0].confidence >= 0.8

    def test_column_name_hint_increases_confidence(self):
        """Column name matching PII type should boost confidence."""
        df = pd.DataFrame(
            {
                "email_address": [
                    "test1@example.com",
                    "test2@example.com",
                    "test3@example.com",
                    "test4@example.com",
                    "test5@example.com",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        assert len(warnings) == 1
        # Column name hint should boost confidence
        assert warnings[0].confidence >= 0.7


class TestMinimumMatchRequirements:
    """Tests for minimum match requirements."""

    def test_requires_minimum_matches(self):
        """Should require at least MIN_MATCHES to flag PII."""
        # Only 2 emails in a column - below threshold
        df = pd.DataFrame(
            {
                "mixed": [
                    "user@example.com",
                    "another@test.com",
                    "not an email",
                    "also not email",
                    "still not",
                ],
            }
        )

        warnings = detect_pii_columns(df)

        # Should not flag with only 2 matches (below MIN_MATCHES=3)
        email_warnings = [w for w in warnings if w.pii_type == PiiType.EMAIL]
        assert len(email_warnings) == 0

    def test_requires_minimum_ratio(self):
        """Should require at least MIN_MATCH_RATIO to flag PII."""
        # Only 3 emails in 100 rows - below 10% threshold
        df = pd.DataFrame(
            {
                "data": (["user@example.com"] * 3 + ["not an email"] * 97),
            }
        )

        warnings = detect_pii_columns(df)

        email_warnings = [w for w in warnings if w.pii_type == PiiType.EMAIL]
        assert len(email_warnings) == 0


class TestMasking:
    """Tests for value masking."""

    def test_masks_email(self):
        """Should mask email showing first char and domain."""
        masked = _mask_value("john@example.com", PiiType.EMAIL)
        assert masked == "j***@example.com"

    def test_masks_ssn(self):
        """Should mask SSN showing last 4 digits."""
        masked = _mask_value("123-45-6789", PiiType.SSN)
        assert masked == "***-**-6789"

    def test_masks_phone(self):
        """Should mask phone showing last 4 digits."""
        masked = _mask_value("(123) 456-7890", PiiType.PHONE)
        assert masked == "(***) ***-7890"

    def test_masks_credit_card(self):
        """Should mask credit card showing last 4 digits."""
        masked = _mask_value("4111 1111 1111 1111", PiiType.CREDIT_CARD)
        assert masked == "****-****-****-1111"

    def test_masks_ip(self):
        """Should mask IP showing first octet."""
        masked = _mask_value("192.168.1.1", PiiType.IP_ADDRESS)
        assert masked == "192.***.***.**"


class TestCsvDetection:
    """Tests for CSV content detection."""

    def test_detect_pii_in_csv_bytes(self):
        """Should detect PII in CSV content bytes."""
        csv_content = b"email,name\nuser@test.com,John\ntest@example.com,Jane\nanother@mail.com,Bob\nfourth@email.net,Alice\nfifth@domain.org,Charlie"

        warnings = detect_pii_in_csv(csv_content)

        email_warnings = [w for w in warnings if w.pii_type == PiiType.EMAIL]
        assert len(email_warnings) == 1

    def test_handles_invalid_csv(self):
        """Should return empty list for invalid CSV."""
        invalid_content = b"not,valid,csv\x00\x01\x02"

        warnings = detect_pii_in_csv(invalid_content)

        # Should not raise, just return empty
        assert isinstance(warnings, list)


class TestMultiplePiiTypes:
    """Tests for detecting multiple PII types."""

    def test_detects_multiple_pii_columns(self):
        """Should detect multiple different PII types."""
        df = pd.DataFrame(
            {
                "email": [f"user{i}@example.com" for i in range(10)],
                "phone": [f"123-456-78{i:02d}" for i in range(10)],
                "data": [f"value_{i}" for i in range(10)],
            }
        )

        warnings = detect_pii_columns(df)

        pii_types = {w.pii_type for w in warnings}
        assert PiiType.EMAIL in pii_types
        assert PiiType.PHONE in pii_types
        assert len(warnings) >= 2


class TestNumericColumns:
    """Tests for numeric column handling."""

    def test_skips_pure_numeric_columns(self):
        """Should skip columns with only numbers."""
        df = pd.DataFrame(
            {
                "quantity": [100, 200, 300, 400, 500],
                "price": [9.99, 19.99, 29.99, 39.99, 49.99],
            }
        )

        warnings = detect_pii_columns(df)

        # Numeric columns should not trigger PII detection
        assert len(warnings) == 0


class TestSortingByConfidence:
    """Tests for warning sorting."""

    def test_warnings_sorted_by_confidence_descending(self):
        """Warnings should be sorted by confidence (highest first)."""
        df = pd.DataFrame(
            {
                "email": [f"user{i}@example.com" for i in range(20)],  # High confidence
                "maybe_phone": ["123-456-7890"] * 5 + ["not phone"] * 15,  # Lower confidence
            }
        )

        warnings = detect_pii_columns(df)

        if len(warnings) > 1:
            confidences = [w.confidence for w in warnings]
            assert confidences == sorted(confidences, reverse=True)
