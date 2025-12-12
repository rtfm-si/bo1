"""Tests for backup monitoring job."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.jobs.backup_monitor import (
    check_backup_health,
    get_backup_age_hours,
    get_latest_backup,
    monitor_backups,
)


class TestGetLatestBackup:
    """Tests for get_latest_backup function."""

    def test_no_directory(self) -> None:
        """Returns None when directory doesn't exist."""
        result = get_latest_backup("/nonexistent/path")
        assert result is None

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Returns None when directory is empty."""
        result = get_latest_backup(str(tmp_path))
        assert result is None

    def test_no_sql_gz_files(self, tmp_path: Path) -> None:
        """Returns None when no .sql.gz files exist."""
        (tmp_path / "other.txt").touch()
        result = get_latest_backup(str(tmp_path))
        assert result is None

    def test_finds_single_backup(self, tmp_path: Path) -> None:
        """Finds single backup file."""
        backup = tmp_path / "backup-20241212.sql.gz"
        backup.touch()
        result = get_latest_backup(str(tmp_path))
        assert result == backup

    def test_finds_latest_backup(self, tmp_path: Path) -> None:
        """Finds most recent backup by mtime."""
        old_backup = tmp_path / "backup-old.sql.gz"
        old_backup.touch()

        # Create newer backup
        import time

        time.sleep(0.01)
        new_backup = tmp_path / "backup-new.sql.gz"
        new_backup.touch()

        result = get_latest_backup(str(tmp_path))
        assert result == new_backup


class TestGetBackupAgeHours:
    """Tests for get_backup_age_hours function."""

    def test_recent_backup(self, tmp_path: Path) -> None:
        """Returns small age for recent backup."""
        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        age = get_backup_age_hours(backup)
        assert age < 0.01  # Less than 36 seconds old

    def test_old_backup(self, tmp_path: Path) -> None:
        """Returns correct age for older backup."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        # Set mtime to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(backup, (old_time, old_time))

        age = get_backup_age_hours(backup)
        assert 24.9 < age < 25.1


class TestCheckBackupHealth:
    """Tests for check_backup_health function."""

    def test_no_backups_critical(self, tmp_path: Path) -> None:
        """Returns critical when no backups found."""
        result = check_backup_health(str(tmp_path))

        assert result["status"] == "critical"
        assert "No backups found" in result["message"]
        assert result["latest_backup"] is None

    def test_fresh_backup_ok(self, tmp_path: Path) -> None:
        """Returns ok for fresh backup."""
        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        result = check_backup_health(str(tmp_path))

        assert result["status"] == "ok"
        assert "healthy" in result["message"]
        assert result["latest_backup"] == "backup.sql.gz"
        assert result["age_hours"] < 1

    def test_warning_threshold(self, tmp_path: Path) -> None:
        """Returns warning when backup exceeds warning threshold."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        # Set mtime to 27 hours ago (past 26h warning)
        old_time = time.time() - (27 * 3600)
        os.utime(backup, (old_time, old_time))

        result = check_backup_health(str(tmp_path))

        assert result["status"] == "warning"
        assert "warning threshold" in result["message"]

    def test_critical_threshold(self, tmp_path: Path) -> None:
        """Returns critical when backup exceeds critical threshold."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        # Set mtime to 50 hours ago (past 48h critical)
        old_time = time.time() - (50 * 3600)
        os.utime(backup, (old_time, old_time))

        result = check_backup_health(str(tmp_path))

        assert result["status"] == "critical"
        assert "critical threshold" in result["message"]

    def test_custom_thresholds(self, tmp_path: Path) -> None:
        """Respects custom thresholds."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        # Set mtime to 5 hours ago
        old_time = time.time() - (5 * 3600)
        os.utime(backup, (old_time, old_time))

        # Default thresholds: should be ok
        result = check_backup_health(str(tmp_path))
        assert result["status"] == "ok"

        # Custom lower threshold: should be warning
        result = check_backup_health(str(tmp_path), max_age_hours=4)
        assert result["status"] == "warning"


class TestMonitorBackups:
    """Tests for monitor_backups async function."""

    @pytest.mark.asyncio
    async def test_healthy_no_alert(self, tmp_path: Path) -> None:
        """No alert sent for healthy backup."""
        backup = tmp_path / "backup.sql.gz"
        backup.touch()

        with patch("backend.jobs.backup_monitor.send_ntfy_alert") as mock_alert:
            result = await monitor_backups(str(tmp_path))

        assert result["status"] == "ok"
        assert result["alert_sent"] is False
        mock_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_warning_sends_alert(self, tmp_path: Path) -> None:
        """Alert sent for warning status."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()
        old_time = time.time() - (27 * 3600)
        os.utime(backup, (old_time, old_time))

        with patch(
            "backend.jobs.backup_monitor.send_ntfy_alert", new_callable=AsyncMock
        ) as mock_alert:
            mock_alert.return_value = True
            with patch.dict(os.environ, {"NTFY_TOPIC_ALERTS": "test-topic"}):
                result = await monitor_backups(str(tmp_path))

        assert result["status"] == "warning"
        assert result["alert_sent"] is True
        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args.kwargs
        assert call_kwargs["priority"] == "high"

    @pytest.mark.asyncio
    async def test_critical_sends_urgent_alert(self, tmp_path: Path) -> None:
        """Urgent alert sent for critical status."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()
        old_time = time.time() - (50 * 3600)
        os.utime(backup, (old_time, old_time))

        with patch(
            "backend.jobs.backup_monitor.send_ntfy_alert", new_callable=AsyncMock
        ) as mock_alert:
            mock_alert.return_value = True
            with patch.dict(os.environ, {"NTFY_TOPIC_ALERTS": "test-topic"}):
                result = await monitor_backups(str(tmp_path))

        assert result["status"] == "critical"
        assert result["alert_sent"] is True
        call_kwargs = mock_alert.call_args.kwargs
        assert call_kwargs["priority"] == "urgent"

    @pytest.mark.asyncio
    async def test_no_alert_when_disabled(self, tmp_path: Path) -> None:
        """No alert when send_alerts=False."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()
        old_time = time.time() - (50 * 3600)
        os.utime(backup, (old_time, old_time))

        with patch("backend.jobs.backup_monitor.send_ntfy_alert") as mock_alert:
            result = await monitor_backups(str(tmp_path), send_alerts=False)

        assert result["status"] == "critical"
        assert result["alert_sent"] is False
        mock_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_alert_when_topic_not_configured(self, tmp_path: Path) -> None:
        """No alert when NTFY_TOPIC_ALERTS not set."""
        import os
        import time

        backup = tmp_path / "backup.sql.gz"
        backup.touch()
        old_time = time.time() - (50 * 3600)
        os.utime(backup, (old_time, old_time))

        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("NTFY_TOPIC_ALERTS", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("backend.jobs.backup_monitor.send_ntfy_alert"):
                result = await monitor_backups(str(tmp_path))

        assert result["status"] == "critical"
        assert result["alert_sent"] is False
