"""Tests for ClamAV antivirus scanner service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.antivirus import (
    ClamAVError,
    ClamAVScanner,
    ScanResult,
    ScanStatus,
    compute_file_hash,
    scan_upload,
)


class TestScanStatus:
    """Tests for ScanStatus enum."""

    def test_scan_status_values(self):
        """Verify enum values match expected strings."""
        assert ScanStatus.CLEAN.value == "clean"
        assert ScanStatus.INFECTED.value == "infected"
        assert ScanStatus.ERROR.value == "error"


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_clean_result(self):
        """Test clean scan result properties."""
        result = ScanResult(status=ScanStatus.CLEAN, scan_duration_ms=10.5)
        assert result.is_clean
        assert not result.is_infected
        assert result.threat_name is None
        assert result.error_message is None

    def test_infected_result(self):
        """Test infected scan result properties."""
        result = ScanResult(
            status=ScanStatus.INFECTED,
            threat_name="Win.Test.EICAR_HDB-1",
            scan_duration_ms=15.0,
        )
        assert not result.is_clean
        assert result.is_infected
        assert result.threat_name == "Win.Test.EICAR_HDB-1"

    def test_error_result(self):
        """Test error scan result properties."""
        result = ScanResult(
            status=ScanStatus.ERROR,
            error_message="Connection refused",
            scan_duration_ms=5.0,
        )
        assert not result.is_clean
        assert not result.is_infected
        assert result.error_message == "Connection refused"


class TestClamAVScanner:
    """Tests for ClamAVScanner class."""

    @pytest.fixture
    def scanner(self):
        """Create a scanner instance with test configuration."""
        return ClamAVScanner(host="localhost", port=3310, timeout=5.0)

    def test_init_defaults(self):
        """Test scanner initialization with defaults."""
        scanner = ClamAVScanner()
        assert scanner.host == "clamav"  # Default from env or fallback
        assert scanner.port == 3310
        assert scanner.timeout == 60.0

    def test_init_custom(self):
        """Test scanner initialization with custom values."""
        scanner = ClamAVScanner(host="test-host", port=1234, timeout=30.0)
        assert scanner.host == "test-host"
        assert scanner.port == 1234
        assert scanner.timeout == 30.0

    def test_parse_response_clean(self, scanner):
        """Test parsing clean scan response."""
        result = scanner._parse_response("stream: OK", 10.0)
        assert result.status == ScanStatus.CLEAN
        assert result.threat_name is None
        assert result.scan_duration_ms == 10.0

    def test_parse_response_infected(self, scanner):
        """Test parsing infected scan response."""
        result = scanner._parse_response("stream: Win.Test.EICAR_HDB-1 FOUND", 15.0)
        assert result.status == ScanStatus.INFECTED
        assert result.threat_name == "Win.Test.EICAR_HDB-1"
        assert result.scan_duration_ms == 15.0

    def test_parse_response_error(self, scanner):
        """Test parsing error scan response."""
        result = scanner._parse_response("stream: UNKNOWN ERROR", 5.0)
        assert result.status == ScanStatus.ERROR
        assert "UNKNOWN ERROR" in result.error_message

    @pytest.mark.asyncio
    async def test_is_healthy_success(self, scanner):
        """Test health check when ClamAV responds with PONG."""
        with patch.object(scanner, "_send_command", new_callable=AsyncMock) as mock_cmd:
            mock_cmd.return_value = "PONG"
            assert await scanner.is_healthy() is True
            mock_cmd.assert_called_once_with("PING")

    @pytest.mark.asyncio
    async def test_is_healthy_failure(self, scanner):
        """Test health check when ClamAV doesn't respond."""
        with patch.object(scanner, "_send_command", new_callable=AsyncMock) as mock_cmd:
            mock_cmd.side_effect = ClamAVError("Connection refused")
            assert await scanner.is_healthy() is False

    @pytest.mark.asyncio
    async def test_get_version_success(self, scanner):
        """Test version retrieval."""
        with patch.object(scanner, "_send_command", new_callable=AsyncMock) as mock_cmd:
            mock_cmd.return_value = "ClamAV 1.4.0/27189/Wed Dec 18 09:24:00 2024"
            version = await scanner.get_version()
            assert "ClamAV 1.4.0" in version

    @pytest.mark.asyncio
    async def test_get_version_failure(self, scanner):
        """Test version retrieval when ClamAV unavailable."""
        with patch.object(scanner, "_send_command", new_callable=AsyncMock) as mock_cmd:
            mock_cmd.side_effect = ClamAVError("Connection refused")
            assert await scanner.get_version() is None


class TestComputeFileHash:
    """Tests for file hash computation."""

    def test_compute_hash(self):
        """Test SHA-256 hash computation."""
        data = b"test content"
        hash_result = compute_file_hash(data)
        # SHA-256 hash is 64 hex characters
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_same_content_same_hash(self):
        """Test that same content produces same hash."""
        data = b"identical content"
        assert compute_file_hash(data) == compute_file_hash(data)

    def test_different_content_different_hash(self):
        """Test that different content produces different hash."""
        assert compute_file_hash(b"content a") != compute_file_hash(b"content b")


class TestScanUpload:
    """Tests for scan_upload convenience function."""

    @pytest.mark.asyncio
    async def test_scan_upload_clean(self):
        """Test scanning clean file."""
        with patch("backend.services.antivirus.get_scanner") as mock_get_scanner:
            mock_scanner = MagicMock()
            mock_scanner.scan_bytes = AsyncMock(
                return_value=ScanResult(status=ScanStatus.CLEAN, scan_duration_ms=10.0)
            )
            mock_get_scanner.return_value = mock_scanner

            result = await scan_upload(b"clean content", "test.csv")

            assert result.is_clean
            mock_scanner.scan_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_upload_infected_logs_quarantine(self):
        """Test that infected files are logged to quarantine."""
        with (
            patch("backend.services.antivirus.get_scanner") as mock_get_scanner,
            patch("backend.services.antivirus.log_quarantine") as mock_log,
            patch("backend.services.antivirus._emit_scan_metrics"),
        ):
            mock_scanner = MagicMock()
            mock_scanner.scan_bytes = AsyncMock(
                return_value=ScanResult(
                    status=ScanStatus.INFECTED,
                    threat_name="TestVirus",
                    scan_duration_ms=15.0,
                )
            )
            mock_get_scanner.return_value = mock_scanner

            result = await scan_upload(
                b"malicious content",
                "evil.csv",
                user_id="user-123",
                content_type="text/csv",
            )

            assert result.is_infected
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["user_id"] == "user-123"
            assert call_args.kwargs["threat_name"] == "TestVirus"

    @pytest.mark.asyncio
    async def test_scan_upload_error_required(self):
        """Test that scan errors raise when ClamAV is required."""
        with patch("backend.services.antivirus.get_scanner") as mock_get_scanner:
            mock_scanner = MagicMock()
            mock_scanner.scan_bytes = AsyncMock(
                return_value=ScanResult(
                    status=ScanStatus.ERROR,
                    error_message="Connection refused",
                    scan_duration_ms=5.0,
                )
            )
            mock_get_scanner.return_value = mock_scanner

            with pytest.raises(ClamAVError, match="Scan required but failed"):
                await scan_upload(b"content", "test.csv", require_scan=True)

    @pytest.mark.asyncio
    async def test_scan_upload_error_optional(self):
        """Test that scan errors return clean when ClamAV is optional."""
        with patch("backend.services.antivirus.get_scanner") as mock_get_scanner:
            mock_scanner = MagicMock()
            mock_scanner.scan_bytes = AsyncMock(
                return_value=ScanResult(
                    status=ScanStatus.ERROR,
                    error_message="Connection refused",
                    scan_duration_ms=5.0,
                )
            )
            mock_get_scanner.return_value = mock_scanner

            result = await scan_upload(b"content", "test.csv", require_scan=False)

            # Should return pending when ClamAV is optional (for later scan)
            assert result.is_pending


class TestEICAR:
    """Integration tests using EICAR test pattern.

    Note: These tests require a running ClamAV instance.
    Skip in CI without ClamAV available.
    """

    # EICAR test signature - standard antivirus test file
    EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    @pytest.fixture
    def scanner(self):
        """Create scanner for integration tests."""
        return ClamAVScanner(host="localhost", port=3310)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scan_eicar_detected(self, scanner):
        """Test that EICAR test pattern is detected as malware.

        Skip if ClamAV is not available.
        """
        if not await scanner.is_healthy():
            pytest.skip("ClamAV not available")

        result = await scanner.scan_bytes(self.EICAR, "eicar.com")
        assert result.is_infected
        assert "EICAR" in (result.threat_name or "")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scan_clean_file(self, scanner):
        """Test that clean file is not detected as malware.

        Skip if ClamAV is not available.
        """
        if not await scanner.is_healthy():
            pytest.skip("ClamAV not available")

        result = await scanner.scan_bytes(b"Just some normal text content", "readme.txt")
        assert result.is_clean
