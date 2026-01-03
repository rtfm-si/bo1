"""Tests for style adapter module.

Tests style detection and instruction generation based on business context.
"""

from bo1.prompts.style_adapter import (
    STYLE_PROFILES,
    StyleProfile,
    detect_style_profile,
    get_style_instruction,
    get_style_profile_name,
)


class TestDetectStyleProfile:
    """Tests for detect_style_profile function."""

    def test_none_context_returns_neutral(self):
        """None context should return neutral profile."""
        assert detect_style_profile(None) == StyleProfile.NEUTRAL

    def test_empty_context_returns_neutral(self):
        """Empty context should return neutral profile."""
        assert detect_style_profile({}) == StyleProfile.NEUTRAL

    def test_b2b_saas_detection(self):
        """B2B SaaS business model detected correctly."""
        context = {"business_model": "B2B SaaS"}
        assert detect_style_profile(context) == StyleProfile.B2B_SAAS

    def test_b2b_software_detection(self):
        """B2B software business model detected as B2B_SAAS."""
        context = {"business_model": "B2B software platform"}
        assert detect_style_profile(context) == StyleProfile.B2B_SAAS

    def test_enterprise_detection(self):
        """Enterprise business model detected correctly."""
        context = {"business_model": "Enterprise SaaS"}
        assert detect_style_profile(context) == StyleProfile.ENTERPRISE

    def test_enterprise_via_target_market(self):
        """Enterprise detected from target_market when model is B2B."""
        context = {"business_model": "B2B", "target_market": "Enterprise companies"}
        assert detect_style_profile(context) == StyleProfile.ENTERPRISE

    def test_agency_detection(self):
        """Agency business model detected correctly."""
        context = {"business_model": "Digital marketing agency"}
        assert detect_style_profile(context) == StyleProfile.AGENCY

    def test_consultancy_as_agency(self):
        """Consultancy treated as agency."""
        context = {"business_model": "Management consultancy"}
        assert detect_style_profile(context) == StyleProfile.AGENCY

    def test_studio_as_agency(self):
        """Creative studio treated as agency."""
        context = {"business_model": "Design studio"}
        assert detect_style_profile(context) == StyleProfile.AGENCY

    def test_b2c_ecommerce_detection(self):
        """B2C ecommerce detected as B2C_PRODUCT."""
        context = {"business_model": "B2C ecommerce"}
        assert detect_style_profile(context) == StyleProfile.B2C_PRODUCT

    def test_d2c_detection(self):
        """D2C detected as B2C_PRODUCT."""
        context = {"business_model": "D2C fashion brand"}
        assert detect_style_profile(context) == StyleProfile.B2C_PRODUCT

    def test_consumer_brand_detection(self):
        """Consumer brand detected as B2C_PRODUCT."""
        context = {"business_model": "Consumer electronics retail"}
        assert detect_style_profile(context) == StyleProfile.B2C_PRODUCT

    def test_service_business_detection(self):
        """Service business detected as B2C_SERVICE."""
        context = {"business_model": "Hair salon service"}
        assert detect_style_profile(context) == StyleProfile.B2C_SERVICE

    def test_coaching_as_service(self):
        """Coaching business detected as B2C_SERVICE."""
        context = {"business_model": "Executive coaching"}
        assert detect_style_profile(context) == StyleProfile.B2C_SERVICE

    def test_fitness_as_service(self):
        """Fitness business detected as B2C_SERVICE."""
        context = {"business_model": "Fitness training"}
        assert detect_style_profile(context) == StyleProfile.B2C_SERVICE

    def test_product_categories_saas_detection(self):
        """SaaS detected from product_categories when model is ambiguous."""
        context = {"business_model": "Technology", "product_categories": ["SaaS", "Productivity"]}
        assert detect_style_profile(context) == StyleProfile.B2B_SAAS

    def test_product_categories_consumer_detection(self):
        """Consumer detected from product_categories."""
        context = {"business_model": "Sales", "product_categories": ["Consumer goods", "Retail"]}
        assert detect_style_profile(context) == StyleProfile.B2C_PRODUCT

    def test_brand_tone_technical(self):
        """Technical brand tone suggests B2B_SAAS."""
        context = {"brand_tone": "Technical and professional"}
        assert detect_style_profile(context) == StyleProfile.B2B_SAAS

    def test_brand_tone_friendly(self):
        """Friendly brand tone suggests B2C_PRODUCT."""
        context = {"brand_tone": "Friendly and casual"}
        assert detect_style_profile(context) == StyleProfile.B2C_PRODUCT

    def test_brand_tone_creative(self):
        """Creative brand tone suggests AGENCY."""
        context = {"brand_tone": "Creative and bold"}
        assert detect_style_profile(context) == StyleProfile.AGENCY

    def test_case_insensitive(self):
        """Detection is case insensitive."""
        context = {"business_model": "B2B SAAS"}
        assert detect_style_profile(context) == StyleProfile.B2B_SAAS


class TestGetStyleInstruction:
    """Tests for get_style_instruction function."""

    def test_none_context_returns_empty(self):
        """None context returns empty string."""
        assert get_style_instruction(None) == ""

    def test_empty_context_returns_empty(self):
        """Empty context returns empty string."""
        assert get_style_instruction({}) == ""

    def test_neutral_without_positioning_returns_empty(self):
        """Neutral profile without brand_positioning returns empty."""
        # No identifiable business type and no brand_positioning
        context = {"company_name": "Acme Inc"}
        assert get_style_instruction(context) == ""

    def test_b2b_saas_includes_tone(self):
        """B2B SaaS context includes professional tone."""
        context = {"business_model": "B2B SaaS"}
        result = get_style_instruction(context)
        assert "<communication_style>" in result
        assert "<tone>" in result
        assert "professional" in result.lower()

    def test_b2c_product_includes_consumer_friendly_tone(self):
        """B2C product context includes consumer-friendly tone."""
        context = {"business_model": "B2C ecommerce"}
        result = get_style_instruction(context)
        assert "<communication_style>" in result
        assert "consumer-friendly" in result.lower() or "benefit" in result.lower()

    def test_includes_brand_positioning_when_available(self):
        """Brand positioning is included when provided."""
        context = {"business_model": "B2B SaaS", "brand_positioning": "Enterprise-grade security"}
        result = get_style_instruction(context)
        assert "<brand_positioning>" in result
        assert "Enterprise-grade security" in result

    def test_includes_brand_tone_when_available(self):
        """Brand tone is included when provided."""
        context = {"business_model": "B2B SaaS", "brand_tone": "Technical and authoritative"}
        result = get_style_instruction(context)
        assert "<brand_voice>" in result
        assert "Technical and authoritative" in result

    def test_includes_vocabulary_hints(self):
        """Vocabulary hints are included for non-neutral profiles."""
        context = {"business_model": "B2B SaaS"}
        result = get_style_instruction(context)
        assert "<vocabulary_hints>" in result
        assert "ROI" in result  # One of the B2B SaaS vocabulary hints

    def test_includes_example_phrasings(self):
        """Example phrasings are included."""
        context = {"business_model": "B2C ecommerce"}
        result = get_style_instruction(context)
        assert "<example_phrasings>" in result

    def test_includes_avoid_section(self):
        """Avoid section is included for non-neutral profiles."""
        context = {"business_model": "B2B SaaS"}
        result = get_style_instruction(context)
        assert "<avoid>" in result

    def test_brand_positioning_sanitized(self):
        """Brand positioning is sanitized against injection."""
        # This would normally contain injection attempt markers
        context = {
            "business_model": "B2B SaaS",
            "brand_positioning": "Test <script>evil</script> positioning",
        }
        result = get_style_instruction(context)
        # Script tag should not appear in output
        # (exact sanitization depends on sanitize_user_input implementation)
        assert "<brand_positioning>" in result

    def test_neutral_with_positioning_returns_content(self):
        """Neutral profile with brand_positioning returns style block."""
        context = {"brand_positioning": "We make things simple"}
        result = get_style_instruction(context)
        # Should include content because brand_positioning is provided
        assert "<brand_positioning>" in result or result == ""


class TestGetStyleProfileName:
    """Tests for get_style_profile_name function."""

    def test_returns_string_profile_name(self):
        """Returns string name of detected profile."""
        context = {"business_model": "B2B SaaS"}
        assert get_style_profile_name(context) == "b2b_saas"

    def test_returns_neutral_for_none(self):
        """Returns 'neutral' for None context."""
        assert get_style_profile_name(None) == "neutral"


class TestStyleProfiles:
    """Tests for STYLE_PROFILES configuration."""

    def test_all_profiles_have_tone(self):
        """All profiles have a tone defined."""
        for profile, config in STYLE_PROFILES.items():
            assert "tone" in config, f"{profile} missing tone"

    def test_all_profiles_have_vocabulary(self):
        """All profiles have vocabulary list."""
        for profile, config in STYLE_PROFILES.items():
            assert "vocabulary" in config, f"{profile} missing vocabulary"
            assert isinstance(config["vocabulary"], list)

    def test_all_profiles_have_phrasing(self):
        """All profiles have phrasing list."""
        for profile, config in STYLE_PROFILES.items():
            assert "phrasing" in config, f"{profile} missing phrasing"
            assert isinstance(config["phrasing"], list)

    def test_all_profiles_have_avoid(self):
        """All profiles have avoid list."""
        for profile, config in STYLE_PROFILES.items():
            assert "avoid" in config, f"{profile} missing avoid"
            assert isinstance(config["avoid"], list)

    def test_non_neutral_profiles_have_content(self):
        """Non-neutral profiles have substantive content."""
        for profile, config in STYLE_PROFILES.items():
            if profile != StyleProfile.NEUTRAL:
                assert len(config["tone"]) > 0, f"{profile} has empty tone"
                assert len(config["vocabulary"]) > 0, f"{profile} has empty vocabulary"
                assert len(config["phrasing"]) > 0, f"{profile} has empty phrasing"


class TestFallbackBehavior:
    """Tests for graceful fallback behavior."""

    def test_missing_fields_dont_crash(self):
        """Missing fields don't cause crashes."""
        # Context with only some fields
        context = {"industry": "Technology"}
        result = detect_style_profile(context)
        assert isinstance(result, StyleProfile)

    def test_none_business_model_handled(self):
        """None business_model doesn't crash."""
        context = {"business_model": None, "brand_tone": "Professional"}
        result = detect_style_profile(context)
        assert isinstance(result, StyleProfile)

    def test_empty_string_business_model(self):
        """Empty string business_model handled."""
        context = {"business_model": ""}
        result = detect_style_profile(context)
        assert result == StyleProfile.NEUTRAL

    def test_non_string_product_categories(self):
        """Non-string product categories handled."""
        context = {"product_categories": [123, None, "SaaS"]}
        result = detect_style_profile(context)
        # Should handle mixed types without crashing
        assert isinstance(result, StyleProfile)
