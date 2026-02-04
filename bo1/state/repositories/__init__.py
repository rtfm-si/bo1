"""Repository Pattern implementation for database operations.

This package provides a clean separation between business logic and data access.
Each repository handles CRUD operations for a specific domain.

Usage:
    from bo1.state.repositories import (
        session_repository,
        user_repository,
        cache_repository,
        contribution_repository,
    )

    # Get a session
    session = session_repository.get(session_id)

    # Save a contribution
    contribution_repository.save(session_id, persona_code, content, ...)
"""

from bo1.state.repositories.auth_provider_repository import (
    AuthProviderRepository,
    auth_provider_repository,
)
from bo1.state.repositories.base import BaseRepository
from bo1.state.repositories.cache_repository import CacheRepository, cache_repository
from bo1.state.repositories.contribution_repository import (
    ContributionRepository,
    contribution_repository,
)
from bo1.state.repositories.decision_repository import (
    DecisionRepository,
    decision_repository,
)
from bo1.state.repositories.feedback_repository import (
    FeedbackRepository,
    feedback_repository,
)
from bo1.state.repositories.gsc_repository import (
    GSCRepository,
    gsc_repository,
)
from bo1.state.repositories.promotion_repository import (
    PromotionRepository,
    promotion_repository,
)
from bo1.state.repositories.session_repository import (
    SessionRepository,
    session_repository,
)
from bo1.state.repositories.template_repository import (
    TemplateRepository,
    template_repository,
)
from bo1.state.repositories.terms_repository import TermsRepository, terms_repository
from bo1.state.repositories.user_repository import UserRepository, user_repository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "user_repository",
    "SessionRepository",
    "session_repository",
    "CacheRepository",
    "cache_repository",
    "ContributionRepository",
    "contribution_repository",
    "DecisionRepository",
    "decision_repository",
    "FeedbackRepository",
    "feedback_repository",
    "GSCRepository",
    "gsc_repository",
    "PromotionRepository",
    "promotion_repository",
    "TemplateRepository",
    "template_repository",
    "TermsRepository",
    "terms_repository",
    "AuthProviderRepository",
    "auth_provider_repository",
]
