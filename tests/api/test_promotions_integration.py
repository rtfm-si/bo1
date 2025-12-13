"""Integration tests for promotions system.

Tests:
- Migration creates tables correctly
- Seed promotions exist
- Repository CRUD operations
- Race condition handling
"""

from datetime import UTC, datetime, timedelta

import pytest

from bo1.state.database import db_session
from bo1.state.repositories.promotion_repository import promotion_repository


@pytest.fixture
def cleanup_test_promotions():
    """Clean up test promotions after each test."""
    test_codes = []
    yield test_codes
    # Cleanup
    with db_session() as conn:
        with conn.cursor() as cur:
            for code in test_codes:
                cur.execute("DELETE FROM promotions WHERE code = %s", (code,))


class TestPromotionsMigration:
    """Tests for migration schema verification."""

    def test_promotions_table_exists(self):
        """Promotions table should exist with correct columns."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'promotions'
                    ORDER BY ordinal_position
                """)
                columns = {row["column_name"]: row["data_type"] for row in cur.fetchall()}

        assert "id" in columns
        assert "code" in columns
        assert "type" in columns
        assert "value" in columns
        assert "max_uses" in columns
        assert "uses_count" in columns
        assert "expires_at" in columns
        assert "created_at" in columns
        assert "is_active" in columns

    def test_user_promotions_table_exists(self):
        """User_promotions table should exist with correct columns."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'user_promotions'
                    ORDER BY ordinal_position
                """)
                columns = {row["column_name"]: row["data_type"] for row in cur.fetchall()}

        assert "id" in columns
        assert "user_id" in columns
        assert "promotion_id" in columns
        assert "applied_at" in columns
        assert "deliberations_remaining" in columns
        assert "discount_applied" in columns
        assert "status" in columns

    def test_promotions_code_index_exists(self):
        """Index on promotions.code should exist."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'promotions' AND indexname = 'ix_promotions_code'
                """)
                result = cur.fetchone()
        assert result is not None

    def test_user_promotions_user_id_index_exists(self):
        """Index on user_promotions.user_id should exist."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'user_promotions'
                      AND indexname = 'ix_user_promotions_user_id'
                """)
                result = cur.fetchone()
        assert result is not None


class TestSeedPromotions:
    """Tests for seed promotion data."""

    def test_welcome10_exists(self):
        """WELCOME10 promotion should exist."""
        promo = promotion_repository.get_promotion_by_code("WELCOME10")
        assert promo is not None
        assert promo["code"] == "WELCOME10"
        assert promo["type"] == "percentage_discount"
        assert float(promo["value"]) == 10.0
        assert promo["max_uses"] == 1000
        assert promo["is_active"] is True

    def test_goodwill5_exists(self):
        """GOODWILL5 promotion should exist."""
        promo = promotion_repository.get_promotion_by_code("GOODWILL5")
        assert promo is not None
        assert promo["code"] == "GOODWILL5"
        assert promo["type"] == "extra_deliberations"
        assert float(promo["value"]) == 5.0
        assert promo["max_uses"] is None  # Unlimited

    def test_launch2025_exists(self):
        """LAUNCH2025 promotion should exist."""
        promo = promotion_repository.get_promotion_by_code("LAUNCH2025")
        assert promo is not None
        assert promo["code"] == "LAUNCH2025"
        assert promo["type"] == "percentage_discount"
        assert float(promo["value"]) == 25.0
        assert promo["max_uses"] == 500
        assert promo["expires_at"] is not None


class TestPromotionRepository:
    """Tests for PromotionRepository methods."""

    def test_get_promotion_by_code_case_insensitive(self):
        """Code lookup should be case-insensitive."""
        promo1 = promotion_repository.get_promotion_by_code("welcome10")
        promo2 = promotion_repository.get_promotion_by_code("WELCOME10")
        promo3 = promotion_repository.get_promotion_by_code("Welcome10")

        assert promo1 is not None
        assert promo2 is not None
        assert promo3 is not None
        assert promo1["id"] == promo2["id"] == promo3["id"]

    def test_get_promotion_by_code_not_found(self):
        """Non-existent code should return None."""
        promo = promotion_repository.get_promotion_by_code("NONEXISTENT")
        assert promo is None

    def test_get_active_promotions(self):
        """Should return only active, non-expired, non-maxed promotions."""
        promos = promotion_repository.get_active_promotions()
        assert len(promos) >= 2  # At least WELCOME10 and GOODWILL5

        for promo in promos:
            assert promo["is_active"] is True
            # Either no expiry or not expired
            if promo["expires_at"]:
                assert promo["expires_at"] > datetime.now(UTC)
            # Either no max or under max
            if promo["max_uses"]:
                assert promo["uses_count"] < promo["max_uses"]

    def test_create_promotion(self, cleanup_test_promotions):
        """Should create a new promotion."""
        code = "TEST_CREATE_123"
        cleanup_test_promotions.append(code)

        promo = promotion_repository.create_promotion(
            code=code,
            promo_type="flat_discount",
            value=50.0,
            max_uses=100,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        assert promo["code"] == code
        assert promo["type"] == "flat_discount"
        assert float(promo["value"]) == 50.0
        assert promo["max_uses"] == 100
        assert promo["uses_count"] == 0
        assert promo["is_active"] is True

    def test_create_promotion_normalizes_code(self, cleanup_test_promotions):
        """Code should be normalized to uppercase."""
        code = "TEST_NORM_456"
        cleanup_test_promotions.append(code)

        promo = promotion_repository.create_promotion(
            code="  test_norm_456  ",
            promo_type="percentage_discount",
            value=15.0,
        )

        assert promo["code"] == code

    def test_deactivate_promotion(self, cleanup_test_promotions):
        """Should deactivate a promotion."""
        code = "TEST_DEACTIVATE"
        cleanup_test_promotions.append(code)

        promo = promotion_repository.create_promotion(
            code=code,
            promo_type="percentage_discount",
            value=10.0,
        )

        result = promotion_repository.deactivate_promotion(promo["id"])
        assert result is True

        updated = promotion_repository.get_promotion_by_id(promo["id"])
        assert updated["is_active"] is False

    def test_increment_promotion_uses(self, cleanup_test_promotions):
        """Should increment uses_count."""
        code = "TEST_INCREMENT"
        cleanup_test_promotions.append(code)

        promo = promotion_repository.create_promotion(
            code=code,
            promo_type="percentage_discount",
            value=10.0,
            max_uses=5,
        )

        # Increment 3 times
        for _ in range(3):
            result = promotion_repository.increment_promotion_uses(promo["id"])
            assert result is True

        updated = promotion_repository.get_promotion_by_id(promo["id"])
        assert updated["uses_count"] == 3

    def test_increment_fails_at_max_uses(self, cleanup_test_promotions):
        """Should fail to increment when at max_uses."""
        code = "TEST_MAX_USES"
        cleanup_test_promotions.append(code)

        promo = promotion_repository.create_promotion(
            code=code,
            promo_type="percentage_discount",
            value=10.0,
            max_uses=2,
        )

        # Increment to max
        promotion_repository.increment_promotion_uses(promo["id"])
        promotion_repository.increment_promotion_uses(promo["id"])

        # Third increment should fail
        result = promotion_repository.increment_promotion_uses(promo["id"])
        assert result is False

        updated = promotion_repository.get_promotion_by_id(promo["id"])
        assert updated["uses_count"] == 2


class TestUserPromotionRepository:
    """Tests for user_promotions operations."""

    @pytest.fixture
    def test_user_id(self):
        """Create a test user for user_promotions tests."""
        test_id = "test-user-promotions-123"
        # Create a test user if it doesn't exist
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, auth_provider, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (test_id, "promo-test@example.com", "email"),
                )
        yield test_id
        # Cleanup user and their promotions after test
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_promotions WHERE user_id = %s", (test_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (test_id,))

    @pytest.fixture
    def test_promotion(self, cleanup_test_promotions):
        """Create a test promotion."""
        code = "TEST_USER_PROMO"
        cleanup_test_promotions.append(code)

        return promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=10.0,
        )

    def test_apply_promotion(self, test_user_id, test_promotion):
        """Should apply a promotion to a user."""
        user_promo = promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promotion["id"],
            deliberations_remaining=10,
        )

        assert user_promo["user_id"] == test_user_id
        assert user_promo["promotion_id"] == test_promotion["id"]
        assert user_promo["deliberations_remaining"] == 10
        assert user_promo["status"] == "active"

    def test_get_user_promotions(self, test_user_id, test_promotion):
        """Should get all promotions for a user."""
        user_promo = promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promotion["id"],
            deliberations_remaining=5,
        )

        promos = promotion_repository.get_user_promotions(test_user_id)
        assert len(promos) >= 1

        # Find our test promo
        found = next((p for p in promos if p["id"] == user_promo["id"]), None)
        assert found is not None
        assert found["promotion"]["code"] == "TEST_USER_PROMO"
        assert found["deliberations_remaining"] == 5

    def test_decrement_deliberations(self, test_user_id, test_promotion):
        """Should decrement deliberations and mark exhausted when reaching 0."""
        user_promo = promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promotion["id"],
            deliberations_remaining=2,
        )

        # First decrement
        remaining = promotion_repository.decrement_deliberations(user_promo["id"], test_user_id)
        assert remaining == 1

        # Second decrement - should mark exhausted
        remaining = promotion_repository.decrement_deliberations(user_promo["id"], test_user_id)
        assert remaining == 0

        # Check status is exhausted
        updated = promotion_repository.get_user_promotion(test_user_id, test_promotion["id"])
        assert updated["status"] == "exhausted"

        # Third decrement should fail (already exhausted)
        remaining = promotion_repository.decrement_deliberations(user_promo["id"], test_user_id)
        assert remaining is None

    def test_update_user_promotion_status(self, test_user_id, test_promotion):
        """Should update user_promotion status."""
        user_promo = promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promotion["id"],
            deliberations_remaining=5,
        )

        result = promotion_repository.update_user_promotion_status(
            user_promo["id"], "expired", test_user_id
        )
        assert result is True

        updated = promotion_repository.get_user_promotion(test_user_id, test_promotion["id"])
        assert updated["status"] == "expired"


class TestPromotionService:
    """Tests for promotion service functions."""

    @pytest.fixture
    def test_user_id(self):
        """Create a test user for service tests."""
        test_id = "test-user-service-456"
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, auth_provider, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (test_id, "service-test@example.com", "email"),
                )
        yield test_id
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_promotions WHERE user_id = %s", (test_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (test_id,))

    @pytest.fixture
    def test_credit_promo(self, cleanup_test_promotions):
        """Create a test credit promotion."""
        code = "TEST_SERVICE_CREDIT"
        cleanup_test_promotions.append(code)
        return promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=5.0,
        )

    @pytest.fixture
    def test_discount_promo(self, cleanup_test_promotions):
        """Create a test discount promotion."""
        code = "TEST_SERVICE_DISCOUNT"
        cleanup_test_promotions.append(code)
        return promotion_repository.create_promotion(
            code=code,
            promo_type="percentage_discount",
            value=10.0,
        )

    def test_check_deliberation_allowance_no_promos(self, test_user_id):
        """User with no promos should have zero allowance."""
        from backend.services.promotion_service import check_deliberation_allowance

        result = check_deliberation_allowance(test_user_id)
        assert result.total_remaining == 0
        assert result.has_credits is False
        assert result.active_promos == []

    def test_check_deliberation_allowance_with_credits(self, test_user_id, test_credit_promo):
        """User with credit promo should have credits."""
        from backend.services.promotion_service import check_deliberation_allowance

        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_credit_promo["id"],
            deliberations_remaining=5,
        )

        result = check_deliberation_allowance(test_user_id)
        assert result.total_remaining == 5
        assert result.has_credits is True
        assert len(result.active_promos) == 1

    def test_consume_promo_deliberation(self, test_user_id, test_credit_promo):
        """Should consume credits from oldest promo."""
        from backend.services.promotion_service import (
            check_deliberation_allowance,
            consume_promo_deliberation,
        )

        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_credit_promo["id"],
            deliberations_remaining=3,
        )

        # Consume one credit
        result = consume_promo_deliberation(test_user_id)
        assert result is True

        # Check remaining
        allowance = check_deliberation_allowance(test_user_id)
        assert allowance.total_remaining == 2

    def test_consume_promo_deliberation_no_credits(self, test_user_id):
        """Should return False when no credits available."""
        from backend.services.promotion_service import consume_promo_deliberation

        result = consume_promo_deliberation(test_user_id)
        assert result is False

    def test_apply_promotions_to_invoice_percentage(self, test_user_id, test_discount_promo):
        """Should apply percentage discount correctly."""
        from backend.services.promotion_service import apply_promotions_to_invoice

        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_discount_promo["id"],
            discount_applied=10.0,
        )

        result = apply_promotions_to_invoice(test_user_id, 100.0)
        assert result.base_amount == 100.0
        assert result.final_amount == 90.0
        assert result.total_discount == 10.0

    def test_apply_promotions_to_invoice_zero_amount(self, test_user_id):
        """Should handle zero invoice amount."""
        from backend.services.promotion_service import apply_promotions_to_invoice

        result = apply_promotions_to_invoice(test_user_id, 0.0)
        assert result.final_amount == 0.0
        assert result.total_discount == 0.0

    def test_validate_and_apply_code_success(self, test_user_id, cleanup_test_promotions):
        """Should successfully apply valid code."""
        from backend.services.promotion_service import validate_and_apply_code

        code = "TEST_APPLY_SUCCESS"
        cleanup_test_promotions.append(code)
        promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=3.0,
        )

        result = validate_and_apply_code(test_user_id, code)
        assert result["status"] == "active"
        assert result["deliberations_remaining"] == 3
        assert result["promotion"]["code"] == code

    def test_validate_and_apply_code_not_found(self, test_user_id):
        """Should raise error for non-existent code."""
        from backend.services.promotion_service import (
            PromoValidationError,
            validate_and_apply_code,
        )

        with pytest.raises(PromoValidationError) as exc_info:
            validate_and_apply_code(test_user_id, "NONEXISTENT")
        assert exc_info.value.code == "not_found"

    def test_validate_and_apply_code_already_applied(self, test_user_id, cleanup_test_promotions):
        """Should reject duplicate application."""
        from backend.services.promotion_service import (
            PromoValidationError,
            validate_and_apply_code,
        )

        code = "TEST_DUPLICATE"
        cleanup_test_promotions.append(code)
        promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=3.0,
        )

        # First apply succeeds
        validate_and_apply_code(test_user_id, code)

        # Second apply fails
        with pytest.raises(PromoValidationError) as exc_info:
            validate_and_apply_code(test_user_id, code)
        assert exc_info.value.code == "already_applied"

    def test_validate_and_apply_code_expired(self, test_user_id, cleanup_test_promotions):
        """Should reject expired promotion."""
        from backend.services.promotion_service import (
            PromoValidationError,
            validate_and_apply_code,
        )

        code = "TEST_EXPIRED"
        cleanup_test_promotions.append(code)
        promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=3.0,
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )

        with pytest.raises(PromoValidationError) as exc_info:
            validate_and_apply_code(test_user_id, code)
        assert exc_info.value.code == "expired"

    def test_validate_and_apply_code_max_uses(self, test_user_id, cleanup_test_promotions):
        """Should reject at-max-uses promotion."""
        from backend.services.promotion_service import (
            PromoValidationError,
            validate_and_apply_code,
        )

        code = "TEST_MAXUSES"
        cleanup_test_promotions.append(code)
        promo = promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=3.0,
            max_uses=1,
        )
        # Use up the promo
        promotion_repository.increment_promotion_uses(promo["id"])

        with pytest.raises(PromoValidationError) as exc_info:
            validate_and_apply_code(test_user_id, code)
        assert exc_info.value.code == "max_uses_reached"


class TestPromotionExpiryJob:
    """Tests for promotion expiry job."""

    @pytest.fixture
    def expired_promo(self, cleanup_test_promotions):
        """Create an expired promotion."""
        code = "TEST_EXPIRY_JOB"
        cleanup_test_promotions.append(code)
        return promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=5.0,
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )

    @pytest.fixture
    def expiry_test_user(self):
        """Create test user for expiry job tests."""
        test_id = "test-user-expiry-789"
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, auth_provider, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (test_id, "expiry-test@example.com", "email"),
                )
        yield test_id
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_promotions WHERE user_id = %s", (test_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (test_id,))

    def test_expiry_job_expires_user_promotions(self, expired_promo, expiry_test_user):
        """Expiry job should mark user_promotions as expired."""
        from backend.jobs.promotion_expiry import run_promotion_expiry

        # Apply expired promo to user
        promotion_repository.apply_promotion(
            user_id=expiry_test_user,
            promotion_id=expired_promo["id"],
            deliberations_remaining=5,
        )

        # Verify active before expiry
        user_promo = promotion_repository.get_user_promotion(expiry_test_user, expired_promo["id"])
        assert user_promo["status"] == "active"

        # Run expiry job
        result = run_promotion_expiry()
        assert result["expired_count"] >= 1

        # Verify expired after job
        user_promo = promotion_repository.get_user_promotion(expiry_test_user, expired_promo["id"])
        assert user_promo["status"] == "expired"


class TestSessionPromoIntegration:
    """Tests for session + promo integration (used_promo_credit flow)."""

    @pytest.fixture
    def test_user_id(self):
        """Create a test user for session tests."""
        test_id = "test-user-session-promo-123"
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, auth_provider, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (test_id, "session-promo-test@example.com", "email"),
                )
        yield test_id
        # Cleanup
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE user_id = %s", (test_id,))
                cur.execute("DELETE FROM user_promotions WHERE user_id = %s", (test_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (test_id,))

    @pytest.fixture
    def test_promo_credit(self, cleanup_test_promotions):
        """Create a test promo with deliberation credits."""
        code = "TEST_SESSION_PROMO"
        cleanup_test_promotions.append(code)
        return promotion_repository.create_promotion(
            code=code,
            promo_type="extra_deliberations",
            value=3.0,
        )

    def test_session_created_with_promo_credit(self, test_user_id, test_promo_credit):
        """Session should store used_promo_credit=True when created with promo."""
        from bo1.state.repositories.session_repository import session_repository

        # Apply promo to user
        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promo_credit["id"],
            deliberations_remaining=3,
        )

        # Create session with promo credit flag
        session = session_repository.create(
            session_id="bo1_test_promo_session",
            user_id=test_user_id,
            problem_statement="Test problem with promo",
            used_promo_credit=True,
        )

        assert session["used_promo_credit"] is True

        # Verify retrieval
        retrieved = session_repository.get("bo1_test_promo_session")
        assert retrieved["used_promo_credit"] is True

    def test_session_created_without_promo_credit(self, test_user_id):
        """Session should store used_promo_credit=False by default."""
        from bo1.state.repositories.session_repository import session_repository

        session = session_repository.create(
            session_id="bo1_test_tier_session",
            user_id=test_user_id,
            problem_statement="Test problem with tier allowance",
        )

        assert session["used_promo_credit"] is False

    def test_promo_credit_consumed_on_completion(self, test_user_id, test_promo_credit):
        """Promo credit should be consumed when session completes."""
        from backend.services.promotion_service import (
            check_deliberation_allowance,
            consume_promo_deliberation,
        )
        from bo1.state.repositories.session_repository import session_repository

        # Apply promo to user with 3 credits
        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promo_credit["id"],
            deliberations_remaining=3,
        )

        # Verify initial credits
        allowance = check_deliberation_allowance(test_user_id)
        assert allowance.total_remaining == 3

        # Create session with promo credit
        session_repository.create(
            session_id="bo1_test_consume_session",
            user_id=test_user_id,
            problem_statement="Test consumption",
            used_promo_credit=True,
        )

        # Simulate completion - consume credit
        consumed = consume_promo_deliberation(test_user_id)
        assert consumed is True

        # Verify credits decremented
        allowance = check_deliberation_allowance(test_user_id)
        assert allowance.total_remaining == 2

    def test_tier_session_does_not_consume_promo(self, test_user_id, test_promo_credit):
        """Tier-based session should not consume promo credits."""
        from backend.services.promotion_service import check_deliberation_allowance
        from bo1.state.repositories.session_repository import session_repository

        # Apply promo to user with 3 credits
        promotion_repository.apply_promotion(
            user_id=test_user_id,
            promotion_id=test_promo_credit["id"],
            deliberations_remaining=3,
        )

        # Create session WITHOUT promo credit (tier-based)
        session_repository.create(
            session_id="bo1_test_tier_only_session",
            user_id=test_user_id,
            problem_statement="Test tier session",
            used_promo_credit=False,
        )

        # Credits should remain unchanged
        allowance = check_deliberation_allowance(test_user_id)
        assert allowance.total_remaining == 3
