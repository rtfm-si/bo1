"""Tests for confidence level validation and normalization."""

from bo1.utils.confidence_parser import (
    VALID_CONFIDENCE_LEVELS,
    validate_confidence_level,
)


class TestValidConfidenceLevels:
    """Tests for valid confidence level constants."""

    def test_valid_levels_defined(self) -> None:
        """VALID_CONFIDENCE_LEVELS should contain exactly HIGH, MEDIUM, LOW."""
        expected = {"HIGH", "MEDIUM", "LOW"}
        assert VALID_CONFIDENCE_LEVELS == expected


class TestValidateConfidenceLevel:
    """Tests for validate_confidence_level function."""

    # === Standard values (pass through) ===

    def test_high_uppercase_passthrough(self) -> None:
        """HIGH should pass through unchanged."""
        assert validate_confidence_level("HIGH") == "HIGH"

    def test_medium_uppercase_passthrough(self) -> None:
        """MEDIUM should pass through unchanged."""
        assert validate_confidence_level("MEDIUM") == "MEDIUM"

    def test_low_uppercase_passthrough(self) -> None:
        """LOW should pass through unchanged."""
        assert validate_confidence_level("LOW") == "LOW"

    # === Case normalization ===

    def test_high_lowercase_normalized(self) -> None:
        """'high' should normalize to HIGH."""
        assert validate_confidence_level("high") == "HIGH"

    def test_medium_lowercase_normalized(self) -> None:
        """'medium' should normalize to MEDIUM."""
        assert validate_confidence_level("medium") == "MEDIUM"

    def test_low_lowercase_normalized(self) -> None:
        """'low' should normalize to LOW."""
        assert validate_confidence_level("low") == "LOW"

    def test_mixed_case_normalized(self) -> None:
        """Mixed case should normalize to uppercase."""
        assert validate_confidence_level("High") == "HIGH"
        assert validate_confidence_level("Medium") == "MEDIUM"
        assert validate_confidence_level("Low") == "LOW"

    # === Variant normalization ===

    def test_very_high_normalizes_to_high(self) -> None:
        """'very high' should normalize to HIGH."""
        assert validate_confidence_level("very high") == "HIGH"

    def test_extremely_high_normalizes_to_high(self) -> None:
        """'extremely high' should normalize to HIGH."""
        assert validate_confidence_level("extremely high") == "HIGH"

    def test_strong_normalizes_to_high(self) -> None:
        """'strong' should normalize to HIGH."""
        assert validate_confidence_level("strong") == "HIGH"

    def test_moderate_normalizes_to_medium(self) -> None:
        """'moderate' should normalize to MEDIUM."""
        assert validate_confidence_level("moderate") == "MEDIUM"

    def test_somewhat_confident_normalizes_to_medium(self) -> None:
        """'somewhat confident' should normalize to MEDIUM."""
        assert validate_confidence_level("somewhat confident") == "MEDIUM"

    def test_fairly_normalizes_to_medium(self) -> None:
        """'fairly confident' should normalize to MEDIUM."""
        assert validate_confidence_level("fairly confident") == "MEDIUM"

    def test_very_low_normalizes_to_low(self) -> None:
        """'very low' should normalize to LOW."""
        assert validate_confidence_level("very low") == "LOW"

    def test_uncertain_normalizes_to_low(self) -> None:
        """'uncertain' should normalize to LOW."""
        assert validate_confidence_level("uncertain") == "LOW"

    def test_weak_normalizes_to_low(self) -> None:
        """'weak' should normalize to LOW."""
        assert validate_confidence_level("weak") == "LOW"

    # === Percentage normalization ===

    def test_85_percent_normalizes_to_high(self) -> None:
        """'85%' should normalize to HIGH (>=70%)."""
        assert validate_confidence_level("85%") == "HIGH"

    def test_70_percent_normalizes_to_high(self) -> None:
        """'70%' should normalize to HIGH (boundary)."""
        assert validate_confidence_level("70%") == "HIGH"

    def test_69_percent_normalizes_to_medium(self) -> None:
        """'69%' should normalize to MEDIUM (40-69%)."""
        assert validate_confidence_level("69%") == "MEDIUM"

    def test_50_percent_normalizes_to_medium(self) -> None:
        """'50%' should normalize to MEDIUM."""
        assert validate_confidence_level("50%") == "MEDIUM"

    def test_40_percent_normalizes_to_medium(self) -> None:
        """'40%' should normalize to MEDIUM (boundary)."""
        assert validate_confidence_level("40%") == "MEDIUM"

    def test_39_percent_normalizes_to_low(self) -> None:
        """'39%' should normalize to LOW (<40%)."""
        assert validate_confidence_level("39%") == "LOW"

    def test_20_percent_normalizes_to_low(self) -> None:
        """'20%' should normalize to LOW."""
        assert validate_confidence_level("20%") == "LOW"

    def test_decimal_confidence_normalized(self) -> None:
        """Decimal values (0-1) should be normalized correctly."""
        assert validate_confidence_level("0.85") == "HIGH"
        assert validate_confidence_level("0.5") == "MEDIUM"
        assert validate_confidence_level("0.3") == "LOW"

    # === Edge cases and defaults ===

    def test_none_defaults_to_medium(self) -> None:
        """None should default to MEDIUM with warning."""
        assert validate_confidence_level(None) == "MEDIUM"

    def test_empty_string_defaults_to_medium(self) -> None:
        """Empty string should default to MEDIUM."""
        assert validate_confidence_level("") == "MEDIUM"

    def test_invalid_value_defaults_to_medium(self) -> None:
        """Invalid/unrecognized values should default to MEDIUM with warning."""
        assert validate_confidence_level("banana") == "MEDIUM"
        assert validate_confidence_level("xyz123") == "MEDIUM"

    def test_whitespace_handling(self) -> None:
        """Whitespace should be stripped."""
        assert validate_confidence_level("  HIGH  ") == "HIGH"
        assert validate_confidence_level("\nmedium\n") == "MEDIUM"
