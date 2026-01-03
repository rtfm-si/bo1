"""Style adapter for tailoring LLM language to user's business context.

Maps business context (brand_tone, business_model, product_categories) to
communication style profiles for natural, context-appropriate responses.
"""

from enum import Enum
from typing import Any

from bo1.prompts.sanitizer import sanitize_user_input


class StyleProfile(str, Enum):
    """Communication style profiles based on business type."""

    B2B_SAAS = "b2b_saas"
    B2C_PRODUCT = "b2c_product"
    B2C_SERVICE = "b2c_service"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"
    NEUTRAL = "neutral"  # Fallback


# Style profile definitions with tone, vocabulary hints, and phrasing patterns
STYLE_PROFILES: dict[StyleProfile, dict[str, Any]] = {
    StyleProfile.B2B_SAAS: {
        "tone": "professional, technical, solution-oriented",
        "vocabulary": [
            "ROI",
            "KPIs",
            "pipeline",
            "churn",
            "MRR/ARR",
            "CAC/LTV",
            "integration",
            "scalability",
        ],
        "phrasing": [
            "This could improve your conversion funnel by...",
            "To reduce churn, consider...",
            "The ROI of this approach...",
        ],
        "avoid": ["cute", "casual", "consumer-focused language"],
    },
    StyleProfile.B2C_PRODUCT: {
        "tone": "consumer-friendly, benefit-focused, approachable",
        "vocabulary": [
            "customers",
            "experience",
            "value",
            "quality",
            "satisfaction",
            "reviews",
            "shopping",
        ],
        "phrasing": [
            "Your customers will love...",
            "This creates a better experience for...",
            "To boost customer satisfaction...",
        ],
        "avoid": ["overly technical jargon", "enterprise-speak"],
    },
    StyleProfile.B2C_SERVICE: {
        "tone": "warm, personal, relationship-focused",
        "vocabulary": [
            "clients",
            "service",
            "experience",
            "satisfaction",
            "booking",
            "appointment",
        ],
        "phrasing": [
            "Your clients will appreciate...",
            "To enhance the service experience...",
            "Building stronger client relationships...",
        ],
        "avoid": ["cold", "transactional language"],
    },
    StyleProfile.AGENCY: {
        "tone": "creative, strategic, partner-like",
        "vocabulary": [
            "campaign",
            "creative",
            "strategy",
            "deliverables",
            "retainer",
            "scope",
            "stakeholders",
        ],
        "phrasing": [
            "From a strategic perspective...",
            "This campaign approach could...",
            "To align with your client's goals...",
        ],
        "avoid": ["overly sales-y language"],
    },
    StyleProfile.ENTERPRISE: {
        "tone": "formal, comprehensive, risk-aware",
        "vocabulary": [
            "stakeholders",
            "governance",
            "compliance",
            "procurement",
            "enterprise-grade",
            "SLA",
        ],
        "phrasing": [
            "To address stakeholder concerns...",
            "From a governance perspective...",
            "Ensuring compliance with...",
        ],
        "avoid": ["startup jargon", "casual language"],
    },
    StyleProfile.NEUTRAL: {
        "tone": "professional, clear, helpful",
        "vocabulary": [],
        "phrasing": [],
        "avoid": [],
    },
}


def detect_style_profile(context: dict[str, Any] | None) -> StyleProfile:
    """Detect the appropriate style profile from business context.

    Args:
        context: Business context dict with brand_tone, business_model, etc.

    Returns:
        StyleProfile enum value based on context analysis
    """
    if not context:
        return StyleProfile.NEUTRAL

    business_model = (context.get("business_model") or "").lower()
    brand_tone = (context.get("brand_tone") or "").lower()
    categories = context.get("product_categories") or []
    target_market = (context.get("target_market") or "").lower()

    # B2B SaaS detection
    b2b_signals = ["b2b", "saas", "enterprise", "software", "platform"]
    if any(signal in business_model for signal in b2b_signals):
        # Check if enterprise-grade
        if "enterprise" in business_model or "enterprise" in target_market:
            return StyleProfile.ENTERPRISE
        return StyleProfile.B2B_SAAS

    # Agency detection
    agency_signals = ["agency", "consultancy", "consulting", "studio"]
    if any(signal in business_model for signal in agency_signals):
        return StyleProfile.AGENCY

    # B2C detection
    b2c_signals = ["b2c", "consumer", "retail", "ecommerce", "e-commerce", "d2c"]
    if any(signal in business_model for signal in b2c_signals):
        return StyleProfile.B2C_PRODUCT

    # Service-based detection
    service_signals = ["service", "clinic", "salon", "spa", "fitness", "coaching"]
    if any(signal in business_model for signal in service_signals):
        return StyleProfile.B2C_SERVICE

    # Check product categories for hints
    category_str = " ".join(str(c).lower() for c in categories)
    if "saas" in category_str or "software" in category_str:
        return StyleProfile.B2B_SAAS
    if "consumer" in category_str or "retail" in category_str:
        return StyleProfile.B2C_PRODUCT

    # Fallback based on brand tone
    if brand_tone:
        if "technical" in brand_tone or "professional" in brand_tone:
            return StyleProfile.B2B_SAAS
        if "friendly" in brand_tone or "casual" in brand_tone:
            return StyleProfile.B2C_PRODUCT
        if "creative" in brand_tone:
            return StyleProfile.AGENCY

    return StyleProfile.NEUTRAL


def get_style_instruction(context: dict[str, Any] | None) -> str:
    """Generate style instruction block for LLM prompts.

    Creates a <communication_style> XML block with guidance tailored to
    the user's business type and brand voice.

    Args:
        context: Business context dict with brand fields

    Returns:
        Style instruction XML block (empty string if no useful context)
    """
    if not context:
        return ""

    profile = detect_style_profile(context)
    profile_config = STYLE_PROFILES[profile]

    # Skip if neutral and no brand_positioning
    if profile == StyleProfile.NEUTRAL and not context.get("brand_positioning"):
        return ""

    lines = ["<communication_style>"]
    lines.append("Adapt your communication style to match the user's business context:")

    # Add tone guidance
    tone = profile_config.get("tone", "")
    if tone:
        lines.append(f"  <tone>{tone}</tone>")

    # Include brand positioning if available
    brand_positioning = context.get("brand_positioning")
    if brand_positioning:
        # Truncate to prevent excessive token usage
        truncated_positioning = str(brand_positioning)[:500]
        safe_positioning = sanitize_user_input(truncated_positioning, context="brand_positioning")
        lines.append(f"  <brand_positioning>{safe_positioning}</brand_positioning>")

    # Include brand tone if available
    brand_tone = context.get("brand_tone")
    if brand_tone:
        # Truncate to prevent excessive token usage
        truncated_tone = str(brand_tone)[:100]
        safe_tone = sanitize_user_input(truncated_tone, context="brand_tone")
        lines.append(f"  <brand_voice>{safe_tone}</brand_voice>")

    # Add vocabulary hints for non-neutral profiles
    vocab = profile_config.get("vocabulary", [])
    if vocab:
        lines.append(f"  <vocabulary_hints>{', '.join(vocab[:6])}</vocabulary_hints>")

    # Add phrasing examples
    phrasing = profile_config.get("phrasing", [])
    if phrasing:
        lines.append("  <example_phrasings>")
        for phrase in phrasing[:2]:
            lines.append(f"    - {phrase}")
        lines.append("  </example_phrasings>")

    # Add things to avoid
    avoid = profile_config.get("avoid", [])
    if avoid:
        lines.append(f"  <avoid>{', '.join(avoid)}</avoid>")

    lines.append("</communication_style>")

    # Only return if we have meaningful content
    if len(lines) > 3:
        return "\n".join(lines)
    return ""


def get_style_profile_name(context: dict[str, Any] | None) -> str:
    """Get the name of the detected style profile.

    Useful for logging and debugging.

    Args:
        context: Business context dict

    Returns:
        Profile name string (e.g., 'b2b_saas', 'b2c_product')
    """
    return detect_style_profile(context).value
