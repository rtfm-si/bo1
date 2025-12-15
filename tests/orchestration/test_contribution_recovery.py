"""Tests for contribution status tracking and recovery.

Tests:
- In-flight contribution persisted before yield
- Status transitions: in_flight → committed, in_flight → rolled_back
- Recovery query finds in-flight contributions
"""

from unittest.mock import MagicMock, patch


class TestContributionStatus:
    """Test contribution status tracking."""

    def test_save_contribution_with_in_flight_status(self):
        """Test that contributions can be saved with in_flight status."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                "id": 123,
                "session_id": "bo1_test",
                "persona_code": "analyst",
                "round_number": 0,
                "phase": "deliberation",
                "status": "in_flight",
                "created_at": "2025-01-01T00:00:00",
            }
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.save_contribution(
                session_id="bo1_test",
                persona_code="analyst",
                content="Test contribution",
                round_number=0,
                phase="deliberation",
                status="in_flight",
                user_id="test_user",
            )

            assert result["id"] == 123
            assert result["status"] == "in_flight"
            # Verify status was passed to INSERT
            call_args = mock_cursor.execute.call_args
            assert "status" in call_args[0][0]
            assert "in_flight" in call_args[0][1]

    def test_update_contribution_status_to_committed(self):
        """Test that in_flight contributions can be committed."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.update_contribution_status(123, "committed")

            assert result is True
            call_args = mock_cursor.execute.call_args
            assert "UPDATE contributions SET status" in call_args[0][0]
            assert call_args[0][1] == ("committed", 123)

    def test_update_contribution_status_to_rolled_back(self):
        """Test that in_flight contributions can be rolled back."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.update_contribution_status(123, "rolled_back")

            assert result is True

    def test_get_in_flight_contributions(self):
        """Test querying in-flight contributions for recovery."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                {
                    "id": 1,
                    "session_id": "bo1_test",
                    "persona_code": "analyst",
                    "content": "First contribution",
                    "round_number": 0,
                    "phase": "deliberation",
                    "cost": 0.01,
                    "tokens": 100,
                    "model": "claude-sonnet",
                    "created_at": "2025-01-01T00:00:00",
                },
                {
                    "id": 2,
                    "session_id": "bo1_test",
                    "persona_code": "critic",
                    "content": "Second contribution",
                    "round_number": 0,
                    "phase": "deliberation",
                    "cost": 0.02,
                    "tokens": 150,
                    "model": "claude-sonnet",
                    "created_at": "2025-01-01T00:01:00",
                },
            ]
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.get_in_flight_contributions("bo1_test")

            assert len(result) == 2
            assert result[0]["persona_code"] == "analyst"
            assert result[1]["persona_code"] == "critic"
            # Verify query filters by status
            call_args = mock_cursor.execute.call_args
            assert "status = 'in_flight'" in call_args[0][0]

    def test_commit_in_flight_contributions(self):
        """Test batch committing all in-flight contributions."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 3
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.commit_in_flight_contributions("bo1_test")

            assert result == 3
            call_args = mock_cursor.execute.call_args
            assert "UPDATE contributions" in call_args[0][0]
            assert "SET status = 'committed'" in call_args[0][0]
            assert "WHERE session_id = %s AND status = 'in_flight'" in call_args[0][0]

    def test_rollback_in_flight_contributions(self):
        """Test batch rolling back all in-flight contributions."""
        with patch("bo1.state.repositories.contribution_repository.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 2
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_conn

            from bo1.state.repositories import contribution_repository

            result = contribution_repository.rollback_in_flight_contributions("bo1_test")

            assert result == 2
            call_args = mock_cursor.execute.call_args
            assert "SET status = 'rolled_back'" in call_args[0][0]


class TestPersonaExecutorRecovery:
    """Test persona executor contribution recovery integration."""

    def test_commit_contributions_calls_repository(self):
        """Test that commit_contributions delegates to repository."""
        from bo1.orchestration.persona_executor import PersonaExecutor

        with patch("bo1.state.repositories.contribution_repository") as mock_repo:
            mock_repo.commit_in_flight_contributions.return_value = 5

            result = PersonaExecutor.commit_contributions("bo1_test")

            assert result == 5
            mock_repo.commit_in_flight_contributions.assert_called_once_with("bo1_test")


class TestContributionMessageMetadata:
    """Test ContributionMessage metadata for recovery."""

    def test_contribution_message_has_metadata_field(self):
        """Test that ContributionMessage supports metadata."""
        from bo1.models.state import ContributionMessage, ContributionType

        msg = ContributionMessage(
            persona_code="analyst",
            persona_name="Data Analyst",
            content="Test content",
            round_number=0,
            contribution_type=ContributionType.INITIAL,
        )

        # Should have default empty dict
        assert msg.metadata == {}

        # Should allow setting contribution_id
        msg.metadata = {"contribution_id": 123}
        assert msg.metadata["contribution_id"] == 123
