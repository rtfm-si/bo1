"""Tests for persona models roundtrip serialization."""

from bo1.models import PersonaCategory, PersonaProfile, PersonaTraits, PersonaType, ResponseStyle


class TestPersonaProfileRoundtrip:
    """Test PersonaProfile model serialization."""

    def test_persona_profile_roundtrip(self, sample_persona_dict: dict) -> None:
        """PersonaProfile with traits dict round-trips correctly."""
        persona = PersonaProfile(**sample_persona_dict)

        # Serialize to JSON
        json_str = persona.model_dump_json()

        # Deserialize back
        restored = PersonaProfile.model_validate_json(json_str)

        assert restored.id == persona.id
        assert restored.code == persona.code
        assert restored.name == persona.name
        assert restored.archetype == persona.archetype
        assert restored.category == persona.category
        assert restored.description == persona.description
        assert restored.emoji == persona.emoji
        assert restored.color_hex == persona.color_hex
        assert restored.traits == persona.traits
        assert restored.default_weight == persona.default_weight
        assert restored.temperature == persona.temperature
        assert restored.system_prompt == persona.system_prompt
        assert restored.response_style == persona.response_style
        assert restored.is_active == persona.is_active
        assert restored.persona_type == persona.persona_type
        assert restored.is_visible == persona.is_visible
        assert restored.display_name == persona.display_name
        assert restored.domain_expertise == persona.domain_expertise

    def test_persona_profile_domain_property(self, sample_persona_dict: dict) -> None:
        """domain property returns archetype."""
        persona = PersonaProfile(**sample_persona_dict)
        assert persona.domain == persona.archetype


class TestPersonaTraitsParsing:
    """Test PersonaTraits parsing and conversion."""

    def test_persona_traits_from_json_string(self) -> None:
        """traits field parses JSON string to dict."""
        data = {
            "id": "test-id",
            "code": "test",
            "name": "Test Persona",
            "archetype": "Test",
            "category": "marketing",
            "description": "Test description",
            "emoji": "🧪",
            "color_hex": "#000000",
            "traits": '{"creative": 0.8, "analytical": 0.7, "optimistic": 0.6, "risk_averse": 0.3, "detail_oriented": 0.5}',
            "default_weight": 1.0,
            "temperature": 0.7,
            "system_prompt": "Test prompt",
            "response_style": "technical",
            "display_name": "Test",
            "domain_expertise": ["test"],
        }
        persona = PersonaProfile(**data)

        assert isinstance(persona.traits, dict)
        assert persona.traits["creative"] == 0.8
        assert persona.traits["analytical"] == 0.7

    def test_persona_traits_from_dict(self) -> None:
        """traits field accepts dict directly."""
        traits_dict = {
            "creative": 0.9,
            "analytical": 0.8,
            "optimistic": 0.7,
            "risk_averse": 0.2,
            "detail_oriented": 0.6,
        }
        data = {
            "id": "test-id",
            "code": "test",
            "name": "Test",
            "archetype": "Test",
            "category": "marketing",
            "description": "Test",
            "emoji": "🧪",
            "color_hex": "#000000",
            "traits": traits_dict,
            "default_weight": 1.0,
            "temperature": 0.7,
            "system_prompt": "Test",
            "response_style": "technical",
            "display_name": "Test",
            "domain_expertise": ["test"],
        }
        persona = PersonaProfile(**data)

        assert persona.traits == traits_dict

    def test_get_traits_converts_dict_to_persona_traits(self, sample_persona_dict: dict) -> None:
        """get_traits() converts dict to PersonaTraits object."""
        persona = PersonaProfile(**sample_persona_dict)
        traits = persona.get_traits()

        assert isinstance(traits, PersonaTraits)
        assert traits.creative == 0.9
        assert traits.analytical == 0.7
        assert traits.optimistic == 0.8
        assert traits.risk_averse == 0.2
        assert traits.detail_oriented == 0.4


class TestDomainExpertisePostgresFormat:
    """Test domain_expertise parsing from PostgreSQL array format."""

    def test_domain_expertise_postgres_array_format(self) -> None:
        """Parses PostgreSQL array format '{val1,val2}'."""
        data = {
            "id": "test-id",
            "code": "test",
            "name": "Test",
            "archetype": "Test",
            "category": "marketing",
            "description": "Test",
            "emoji": "🧪",
            "color_hex": "#000000",
            "traits": {
                "creative": 0.5,
                "analytical": 0.5,
                "optimistic": 0.5,
                "risk_averse": 0.5,
                "detail_oriented": 0.5,
            },
            "default_weight": 1.0,
            "temperature": 0.7,
            "system_prompt": "Test",
            "response_style": "technical",
            "display_name": "Test",
            "domain_expertise": "{technical,strategic,operational}",
        }
        persona = PersonaProfile(**data)

        assert persona.domain_expertise == ["technical", "strategic", "operational"]

    def test_domain_expertise_list_passthrough(self) -> None:
        """List input passes through unchanged."""
        data = {
            "id": "test-id",
            "code": "test",
            "name": "Test",
            "archetype": "Test",
            "category": "marketing",
            "description": "Test",
            "emoji": "🧪",
            "color_hex": "#000000",
            "traits": {
                "creative": 0.5,
                "analytical": 0.5,
                "optimistic": 0.5,
                "risk_averse": 0.5,
                "detail_oriented": 0.5,
            },
            "default_weight": 1.0,
            "temperature": 0.7,
            "system_prompt": "Test",
            "response_style": "technical",
            "display_name": "Test",
            "domain_expertise": ["technical", "strategic"],
        }
        persona = PersonaProfile(**data)

        assert persona.domain_expertise == ["technical", "strategic"]

    def test_domain_expertise_single_string(self) -> None:
        """Single string becomes single-item list."""
        data = {
            "id": "test-id",
            "code": "test",
            "name": "Test",
            "archetype": "Test",
            "category": "marketing",
            "description": "Test",
            "emoji": "🧪",
            "color_hex": "#000000",
            "traits": {
                "creative": 0.5,
                "analytical": 0.5,
                "optimistic": 0.5,
                "risk_averse": 0.5,
                "detail_oriented": 0.5,
            },
            "default_weight": 1.0,
            "temperature": 0.7,
            "system_prompt": "Test",
            "response_style": "technical",
            "display_name": "Test",
            "domain_expertise": "technical",
        }
        persona = PersonaProfile(**data)

        assert persona.domain_expertise == ["technical"]


class TestPersonaCategoryEnum:
    """Test PersonaCategory enum completeness."""

    def test_persona_category_enum_completeness(self) -> None:
        """All expected category values are present."""
        expected_categories = {
            "marketing",
            "finance",
            "legal",
            "product",
            "tech",
            "ops",
            "leadership",
            "data",
            "sales",
            "strategy",
            "customer",
            "innovation",
            "wellness",
            "ethics",
            "community",
            "meta",
            "masked",
        }
        actual_categories = {e.value for e in PersonaCategory}
        assert actual_categories == expected_categories

    def test_persona_category_serialization(self) -> None:
        """Category enum serializes as string value."""
        for category in PersonaCategory:
            assert PersonaCategory(category.value) == category


class TestPersonaTypeEnum:
    """Test PersonaType enum."""

    def test_persona_type_values(self) -> None:
        """All persona types are present."""
        expected = {"standard", "moderator", "facilitator", "research", "meta"}
        actual = {e.value for e in PersonaType}
        assert actual == expected


class TestResponseStyleEnum:
    """Test ResponseStyle enum."""

    def test_response_style_values(self) -> None:
        """All response styles are present."""
        expected = {"technical", "analytical", "narrative", "socratic"}
        actual = {e.value for e in ResponseStyle}
        assert actual == expected
