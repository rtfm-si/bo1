"""Tests for RatingsRepository validation logic.

Validates:
- Input validation for entity_type
- Input validation for rating values
"""

from uuid import uuid4

import pytest


class TestRatingsRepositoryValidation:
    """Test input validation in RatingsRepository."""

    def test_validates_entity_type_meeting(self):
        """Verify 'meeting' is a valid entity type."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        # Should not raise - just test the validation logic
        # Actual DB call would fail but validation should pass
        try:
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=1,
            )
        except ValueError:
            pytest.fail("'meeting' should be a valid entity_type")
        except Exception:  # noqa: S110
            # Expected - no DB connection, but validation passed
            pass

    def test_validates_entity_type_action(self):
        """Verify 'action' is a valid entity type."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        try:
            repo.upsert_rating(
                user_id="test-user",
                entity_type="action",
                entity_id=str(uuid4()),
                rating=-1,
            )
        except ValueError:
            pytest.fail("'action' should be a valid entity_type")
        except Exception:  # noqa: S110
            pass

    def test_rejects_invalid_entity_type(self):
        """Verify invalid entity_type raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="entity_type must be"):
            repo.upsert_rating(
                user_id="test-user",
                entity_type="invalid",
                entity_id=str(uuid4()),
                rating=1,
            )

    def test_rejects_empty_entity_type(self):
        """Verify empty entity_type raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="entity_type must be"):
            repo.upsert_rating(
                user_id="test-user",
                entity_type="",
                entity_id=str(uuid4()),
                rating=1,
            )

    def test_validates_rating_thumbs_up(self):
        """Verify +1 (thumbs up) is a valid rating."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        try:
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=1,
            )
        except ValueError as e:
            if "rating" in str(e):
                pytest.fail("+1 should be a valid rating")
        except Exception:  # noqa: S110
            pass

    def test_validates_rating_thumbs_down(self):
        """Verify -1 (thumbs down) is a valid rating."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        try:
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=-1,
            )
        except ValueError as e:
            if "rating" in str(e):
                pytest.fail("-1 should be a valid rating")
        except Exception:  # noqa: S110
            pass

    def test_rejects_rating_zero(self):
        """Verify 0 rating raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="rating must be -1 or 1"):
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=0,
            )

    def test_rejects_rating_two(self):
        """Verify 2 rating raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="rating must be -1 or 1"):
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=2,
            )

    def test_rejects_empty_user_id(self):
        """Verify empty user_id raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            repo.upsert_rating(
                user_id="",
                entity_type="meeting",
                entity_id=str(uuid4()),
                rating=1,
            )

    def test_rejects_empty_entity_id(self):
        """Verify empty entity_id raises ValueError."""
        from bo1.state.repositories.ratings_repository import RatingsRepository

        repo = RatingsRepository()
        with pytest.raises(ValueError, match="entity_id must be a non-empty string"):
            repo.upsert_rating(
                user_id="test-user",
                entity_type="meeting",
                entity_id="",
                rating=1,
            )
