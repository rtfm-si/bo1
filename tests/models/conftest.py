"""Shared fixtures for model validation tests."""

from datetime import UTC, datetime

import pytest


@pytest.fixture
def sample_session_dict() -> dict:
    """Realistic Session data matching DB schema."""
    return {
        "id": "bo1_abc12345-6789-0abc-def0-123456789012",
        "user_id": "user_test_123",
        "problem_statement": "How should we allocate Q1 marketing budget?",
        "problem_context": {"industry": "SaaS", "budget": 50000},
        "status": "running",
        "phase": "discussion",
        "total_cost": 0.25,
        "round_number": 2,
        "created_at": datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        "updated_at": datetime(2024, 1, 15, 11, 45, 0, tzinfo=UTC),
        "synthesis_text": None,
        "final_recommendation": None,
    }


@pytest.fixture
def sample_contribution_dict() -> dict:
    """Realistic ContributionMessage data matching DB schema."""
    return {
        "id": 42,
        "session_id": "bo1_abc12345-6789-0abc-def0-123456789012",
        "persona_code": "growth_hacker",
        "persona_name": "Zara Morales",
        "content": "I recommend focusing on product-led growth strategies...",
        "thinking": "Analyzing growth channels and their potential ROI...",
        "round_number": 1,
        "phase": "exploration",
        "cost": 0.0015,
        "tokens": 250,
        "model": "claude-sonnet-4-20250514",
        "embedding": None,
        "created_at": datetime(2024, 1, 15, 10, 35, 0, tzinfo=UTC),
    }


@pytest.fixture
def sample_persona_dict() -> dict:
    """Realistic PersonaProfile data matching DB schema."""
    return {
        "id": "9e9979e7-4a97-441c-b5ef-59c93326a2aa",
        "code": "growth_hacker",
        "name": "Zara Morales",
        "archetype": "Growth Hacker",
        "category": "marketing",
        "description": "Growth experimentation expert focusing on user acquisition and retention strategies.",
        "emoji": "📈",
        "color_hex": "#EF4444",
        "traits": {
            "creative": 0.9,
            "analytical": 0.7,
            "optimistic": 0.8,
            "risk_averse": 0.2,
            "detail_oriented": 0.4,
        },
        "default_weight": 0.9,
        "temperature": 0.85,
        "system_prompt": "<system_role>You are Zara Morales, a growth hacker...</system_role>",
        "response_style": "technical",
        "is_active": True,
        "persona_type": "standard",
        "is_visible": True,
        "display_name": "Zara",
        "domain_expertise": ["technical", "strategic"],
    }


@pytest.fixture
def sample_problem_dict() -> dict:
    """Realistic Problem data with sub-problems."""
    return {
        "title": "Q1 Marketing Budget Allocation",
        "description": "Determine optimal allocation of $50K marketing budget across channels.",
        "context": "Early-stage B2B SaaS, 6 months runway, targeting SMB segment.",
        "constraints": [
            {"type": "budget", "description": "Total budget", "value": 50000},
            {"type": "time", "description": "Must launch by Q1 end", "value": "90 days"},
        ],
        "sub_problems": [
            {
                "id": "sp_001",
                "goal": "Determine channel mix",
                "context": "Need to balance paid and organic channels",
                "complexity_score": 6,
                "dependencies": [],
                "constraints": [],
                "focus": None,
            },
            {
                "id": "sp_002",
                "goal": "Set CAC targets per channel",
                "context": "Current CAC is $200, need to reduce",
                "complexity_score": 5,
                "dependencies": ["sp_001"],
                "constraints": [],
                "focus": None,
            },
        ],
    }


@pytest.fixture
def sample_recommendation_dict() -> dict:
    """Realistic Recommendation data."""
    return {
        "persona_code": "finance_strategist",
        "persona_name": "Maria Santos",
        "recommendation": "Allocate 60% to content marketing, 40% to paid search",
        "reasoning": "Content marketing has shown 3x ROI in similar B2B SaaS companies. Paid search provides faster feedback loop for optimization.",
        "confidence": 0.85,
        "conditions": [
            "Review monthly and rebalance based on CAC",
            "Set up proper attribution tracking first",
        ],
        "weight": 1.1,
        "alternatives_considered": ["100% content (slower)", "100% paid (expensive)"],
        "risk_assessment": "Content takes 6+ months to show results",
    }
