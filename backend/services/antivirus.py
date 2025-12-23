"""ClamAV antivirus scanner service.

Provides async scanning of files and bytes using ClamAV daemon via TCP socket.
Used to scan user-uploaded files before storage/processing.
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Metrics imports - defer to avoid circular import issues
_metrics_initialized = False


def _get_metrics() -> None:
    """Lazy import metrics to avoid circular imports."""
    global _metrics_initialized
    if not _metrics_initialized:
        try:
            from backend.api.middleware.metrics import (
                bo1_file_pending_scan_total,
                bo1_file_quarantine_total,
                bo1_file_scan_duration_seconds,
                bo1_file_scan_total,
            )

            _metrics_initialized = True
            return (
                bo1_file_scan_total,
                bo1_file_scan_duration_seconds,
                bo1_file_quarantine_total,
                bo1_file_pending_scan_total,
            )
        except ImportError:
            return None, None, None, None
    from backend.api.middleware.metrics import (
        bo1_file_pending_scan_total,
        bo1_file_quarantine_total,
        bo1_file_scan_duration_seconds,
        bo1_file_scan_total,
    )

    return (
        bo1_file_scan_total,
        bo1_file_scan_duration_seconds,
        bo1_file_quarantine_total,
        bo1_file_pending_scan_total,
    )


class ScanStatus(str, Enum):
    """Scan result status."""

    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    PENDING = "pending"  # ClamAV unavailable, file stored for later scan


@dataclass
class ScanResult:
    """Result of a ClamAV scan.

    Attributes:
        status: Scan result status (clean/infected/error)
        threat_name: Name of detected threat, if any
        scan_duration_ms: Time taken to scan in milliseconds
        error_message: Error message if scan failed
    """

    status: ScanStatus
    threat_name: str | None = None
    scan_duration_ms: float = 0.0
    error_message: str | None = None

    @property
    def is_clean(self) -> bool:
        """Check if the scan result is clean."""
        return self.status == ScanStatus.CLEAN

    @property
    def is_infected(self) -> bool:
        """Check if a threat was detected."""
        return self.status == ScanStatus.INFECTED

    @property
    def is_pending(self) -> bool:
        """Check if scan is pending (ClamAV was unavailable)."""
        return self.status == ScanStatus.PENDING


class ClamAVError(Exception):
    """ClamAV scanner error."""


def _emit_scan_metrics(result: ScanResult, threat_name: str | None = None) -> None:
    """Emit Prometheus metrics for scan result."""
    try:
        scan_total, duration_hist, quarantine_total, pending_total = _get_metrics()
        if scan_total is None:
            return

        # Record scan result counter
        scan_total.labels(result=result.status.value).inc()

        # Record scan duration
        duration_hist.observe(result.scan_duration_ms / 1000.0)

        # Record quarantine if infected
        if result.status == ScanStatus.INFECTED and threat_name:
            # Extract threat family from full name (e.g., "Win.Test.EICAR" -> "Win")
            threat_type = threat_name.split(".")[0] if "." in threat_name else threat_name
            quarantine_total.labels(threat_type=threat_type).inc()

        # Record pending scan
        if result.status == ScanStatus.PENDING and pending_total:
            pending_total.inc()
    except Exception as e:
        logger.debug(f"Failed to emit scan metrics: {e}")


class ClamAVScanner:
    """ClamAV daemon client using TCP socket protocol.

    The ClamAV daemon uses a simple text protocol:
    - Commands: PING, VERSION, INSTREAM, etc.
    - INSTREAM: Send file data in chunks, terminated by zero-length chunk
    - Response format: "stream: OK" or "stream: <threat> FOUND"
    """

    # Configuration from environment
    CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "clamav")
    CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
    CLAMAV_TIMEOUT_SECONDS = float(os.environ.get("CLAMAV_TIMEOUT_SECONDS", "60.0"))
    CLAMAV_REQUIRED = os.environ.get("CLAMAV_REQUIRED", "false").lower() == "true"
    CLAMAV_CHUNK_SIZE = 8192  # 8KB chunks for streaming

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize ClamAV scanner.

        Args:
            host: ClamAV daemon host (default from CLAMAV_HOST env)
            port: ClamAV daemon port (default from CLAMAV_PORT env)
            timeout: Scan timeout in seconds (default from CLAMAV_TIMEOUT_SECONDS env)
        """
        self.host = host or self.CLAMAV_HOST
        self.port = port or self.CLAMAV_PORT
        self.timeout = timeout or self.CLAMAV_TIMEOUT_SECONDS

    async def _send_command(self, command: str) -> str:
        """Send a command to ClamAV daemon and get response.

        Args:
            command: ClamAV protocol command (e.g., "PING", "VERSION")

        Returns:
            Response string from daemon

        Raises:
            ClamAVError: On connection or protocol error
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            try:
                writer.write(f"n{command}\n".encode())
                await writer.drain()

                response = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=self.timeout,
                )
                return response.decode().strip()
            finally:
                writer.close()
                await writer.wait_closed()
        except TimeoutError as e:
            raise ClamAVError(f"Connection timeout after {self.timeout}s") from e
        except ConnectionRefusedError as e:
            raise ClamAVError(f"Connection refused to {self.host}:{self.port}") from e
        except OSError as e:
            raise ClamAVError(f"Network error: {e}") from e

    async def is_healthy(self) -> bool:
        """Check if ClamAV daemon is running and responsive.

        Returns:
            True if daemon responds to PING, False otherwise
        """
        try:
            response = await self._send_command("PING")
            return response == "PONG"
        except ClamAVError:
            return False

    async def get_version(self) -> str | None:
        """Get ClamAV version and database info.

        Returns:
            Version string or None on error
        """
        try:
            return await self._send_command("VERSION")
        except ClamAVError:
            return None

    async def scan_bytes(self, data: bytes, filename: str = "upload") -> ScanResult:
        """Scan bytes data for malware.

        Uses INSTREAM protocol to send data in chunks without requiring
        the file to be on the ClamAV host filesystem.

        Args:
            data: Bytes to scan
            filename: Optional filename for logging

        Returns:
            ScanResult with status and threat info
        """
        start_time = time.perf_counter()
        data_size = len(data)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            try:
                # Send INSTREAM command
                writer.write(b"nINSTREAM\n")
                await writer.drain()

                # Send data in chunks with size prefix (network byte order)
                offset = 0
                while offset < data_size:
                    chunk = data[offset : offset + self.CLAMAV_CHUNK_SIZE]
                    chunk_size = len(chunk)
                    # Size prefix as 4-byte big-endian integer
                    writer.write(chunk_size.to_bytes(4, "big"))
                    writer.write(chunk)
                    await writer.drain()
                    offset += chunk_size

                # Send zero-length chunk to signal end
                writer.write((0).to_bytes(4, "big"))
                await writer.drain()

                # Read response
                response = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=self.timeout,
                )
                response_text = response.decode().strip()

                duration_ms = (time.perf_counter() - start_time) * 1000

                return self._parse_response(response_text, duration_ms)

            finally:
                writer.close()
                await writer.wait_closed()

        except TimeoutError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                f"ClamAV scan timeout for {filename} ({data_size} bytes) after {duration_ms:.1f}ms"
            )
            return ScanResult(
                status=ScanStatus.ERROR,
                error_message=f"Scan timeout after {self.timeout}s",
                scan_duration_ms=duration_ms,
            )
        except ConnectionRefusedError:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"ClamAV connection refused for {filename}")
            return ScanResult(
                status=ScanStatus.ERROR,
                error_message=f"Connection refused to {self.host}:{self.port}",
                scan_duration_ms=duration_ms,
            )
        except OSError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"ClamAV network error for {filename}: {e}")
            return ScanResult(
                status=ScanStatus.ERROR,
                error_message=str(e),
                scan_duration_ms=duration_ms,
            )

    def _parse_response(self, response: str, duration_ms: float) -> ScanResult:
        """Parse ClamAV scan response.

        Response formats:
        - Clean: "stream: OK"
        - Infected: "stream: Win.Test.EICAR_HDB-1 FOUND"
        - Error: "stream: ... ERROR"

        Args:
            response: Raw response string from ClamAV
            duration_ms: Scan duration in milliseconds

        Returns:
            Parsed ScanResult
        """
        if response.endswith("OK"):
            return ScanResult(
                status=ScanStatus.CLEAN,
                scan_duration_ms=duration_ms,
            )
        elif "FOUND" in response:
            # Extract threat name from "stream: <threat> FOUND"
            threat_name = response.replace("stream:", "").replace("FOUND", "").strip()
            return ScanResult(
                status=ScanStatus.INFECTED,
                threat_name=threat_name,
                scan_duration_ms=duration_ms,
            )
        else:
            # Unexpected response format
            return ScanResult(
                status=ScanStatus.ERROR,
                error_message=f"Unexpected response: {response}",
                scan_duration_ms=duration_ms,
            )


# Singleton instance
_scanner: ClamAVScanner | None = None


def get_scanner() -> ClamAVScanner:
    """Get singleton ClamAV scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = ClamAVScanner()
    return _scanner


def log_quarantine(
    user_id: str,
    file_hash: str,
    threat_name: str,
    original_filename: str | None = None,
    file_size_bytes: int | None = None,
    content_type: str | None = None,
    scan_duration_ms: float | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Log a quarantined file to the database for admin review.

    Args:
        user_id: ID of user who uploaded the file
        file_hash: SHA-256 hash of file content
        threat_name: ClamAV threat identifier
        original_filename: User-provided filename
        file_size_bytes: Size of file in bytes
        content_type: MIME type
        scan_duration_ms: Scan duration in milliseconds
        source_ip: Client IP address
        user_agent: Client user agent
    """
    try:
        with db_session(user_id=user_id) as cursor:
            cursor.execute(
                """
                INSERT INTO file_quarantine (
                    user_id, file_hash, threat_name, original_filename,
                    file_size_bytes, content_type, scan_duration_ms,
                    source_ip, user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    file_hash,
                    threat_name,
                    original_filename,
                    file_size_bytes,
                    content_type,
                    scan_duration_ms,
                    source_ip,
                    user_agent,
                ),
            )
        logger.info(
            f"Quarantined file logged: user={user_id}, threat={threat_name}, hash={file_hash[:16]}..."
        )
    except Exception as e:
        # Don't fail the upload rejection if quarantine logging fails
        logger.error(f"Failed to log quarantined file: {e}")


def compute_file_hash(data: bytes) -> str:
    """Compute SHA-256 hash of file data."""
    return hashlib.sha256(data).hexdigest()


def log_pending_scan(
    file_key: str,
    user_id: str,
    file_hash: str,
    original_filename: str | None = None,
    file_size_bytes: int | None = None,
    content_type: str | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
) -> str | None:
    """Log a file as pending scan when ClamAV is unavailable.

    Args:
        file_key: Storage key/path where file is stored (for retrieval during scan)
        user_id: ID of user who uploaded the file
        file_hash: SHA-256 hash of file content
        original_filename: User-provided filename
        file_size_bytes: Size of file in bytes
        content_type: MIME type
        source_ip: Client IP address
        user_agent: Client user agent

    Returns:
        UUID of pending scan record, or None on error
    """
    try:
        with db_session(user_id=user_id) as cursor:
            cursor.execute(
                """
                INSERT INTO file_pending_scan (
                    file_key, user_id, file_hash, original_filename,
                    file_size_bytes, content_type, source_ip, user_agent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    file_key,
                    user_id,
                    file_hash,
                    original_filename,
                    file_size_bytes,
                    content_type,
                    source_ip,
                    user_agent,
                ),
            )
            row = cursor.fetchone()
            pending_id = str(row[0]) if row else None
        logger.info(
            f"Pending scan logged: user={user_id}, file_key={file_key}, hash={file_hash[:16]}..."
        )
        return pending_id
    except Exception as e:
        # Don't fail the upload if pending scan logging fails
        logger.error(f"Failed to log pending scan: {e}")
        return None


async def scan_pending_files(limit: int = 100) -> dict[str, int]:
    """Scan files that were uploaded when ClamAV was unavailable.

    This should be called periodically (e.g., by a cron job or background worker)
    when ClamAV becomes available.

    Args:
        limit: Maximum number of files to scan in one batch

    Returns:
        Dict with counts: {scanned, clean, infected, errors}
    """
    scanner = get_scanner()

    # Check if ClamAV is healthy
    if not await scanner.is_healthy():
        logger.warning("ClamAV still unavailable, cannot scan pending files")
        return {"scanned": 0, "clean": 0, "infected": 0, "errors": 0}

    stats = {"scanned": 0, "clean": 0, "infected": 0, "errors": 0}

    # Get pending files from database
    try:
        from backend.services.spaces import get_spaces_client

        spaces = get_spaces_client()

        with db_session() as cursor:
            cursor.execute(
                """
                SELECT id, file_key, user_id, file_hash, original_filename,
                       file_size_bytes, content_type, source_ip, user_agent
                FROM file_pending_scan
                WHERE scanned_at IS NULL
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            pending_files = cursor.fetchall()

        for row in pending_files:
            (
                pending_id,
                file_key,
                user_id,
                file_hash,
                filename,
                size,
                content_type,
                source_ip,
                user_agent,
            ) = row

            try:
                # Fetch file from storage
                file_data = spaces.get_file_bytes(file_key)
                if file_data is None:
                    logger.warning(f"Pending file not found in storage: {file_key}")
                    _mark_pending_scan_complete(pending_id, "file_not_found")
                    stats["errors"] += 1
                    continue

                # Scan the file
                result = await scanner.scan_bytes(file_data, filename or file_key)
                _emit_scan_metrics(result, result.threat_name)
                stats["scanned"] += 1

                if result.status == ScanStatus.CLEAN:
                    _mark_pending_scan_complete(pending_id, "clean")
                    stats["clean"] += 1
                elif result.status == ScanStatus.INFECTED:
                    # Log to quarantine and delete the file
                    log_quarantine(
                        user_id=user_id,
                        file_hash=file_hash,
                        threat_name=result.threat_name or "unknown",
                        original_filename=filename,
                        file_size_bytes=size,
                        content_type=content_type,
                        scan_duration_ms=result.scan_duration_ms,
                        source_ip=source_ip,
                        user_agent=user_agent,
                    )
                    # Delete infected file from storage
                    try:
                        spaces.delete_file(file_key)
                        logger.info(f"Deleted infected file from storage: {file_key}")
                    except Exception as e:
                        logger.error(f"Failed to delete infected file {file_key}: {e}")
                    _mark_pending_scan_complete(pending_id, "infected", result.threat_name)
                    stats["infected"] += 1
                else:
                    # Scan error - leave pending for retry
                    logger.warning(
                        f"Scan error for pending file {file_key}: {result.error_message}"
                    )
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"Error scanning pending file {file_key}: {e}")
                stats["errors"] += 1

    except Exception as e:
        logger.error(f"Error fetching pending scans: {e}")

    logger.info(
        f"Pending scan batch complete: scanned={stats['scanned']}, "
        f"clean={stats['clean']}, infected={stats['infected']}, errors={stats['errors']}"
    )
    return stats


def _mark_pending_scan_complete(
    pending_id: str,
    scan_result: str,
    threat_name: str | None = None,
) -> None:
    """Mark a pending scan as completed."""
    try:
        with db_session() as cursor:
            cursor.execute(
                """
                UPDATE file_pending_scan
                SET scanned_at = NOW(), scan_result = %s, threat_name = %s
                WHERE id = %s
                """,
                (scan_result, threat_name, pending_id),
            )
    except Exception as e:
        logger.error(f"Failed to mark pending scan complete: {e}")


async def scan_upload(
    data: bytes,
    filename: str = "upload",
    require_scan: bool | None = None,
    user_id: str | None = None,
    content_type: str | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
    file_key: str | None = None,
) -> ScanResult:
    """Convenience function to scan uploaded file data.

    Handles graceful degradation when ClamAV is unavailable based on
    CLAMAV_REQUIRED environment variable. Logs infected files to quarantine table.
    When ClamAV is unavailable and not required, marks file as PENDING for later scan.

    Args:
        data: File bytes to scan
        filename: Original filename for logging
        require_scan: Override CLAMAV_REQUIRED setting
        user_id: User ID for quarantine logging
        content_type: MIME type for quarantine logging
        source_ip: Client IP for quarantine logging
        user_agent: Client user agent for quarantine logging
        file_key: Storage key for pending scan (required when ClamAV unavailable)

    Returns:
        ScanResult - PENDING if ClamAV unavailable and not required

    Raises:
        ClamAVError: If scan required but ClamAV unavailable
    """
    scanner = get_scanner()
    is_required = require_scan if require_scan is not None else ClamAVScanner.CLAMAV_REQUIRED

    result = await scanner.scan_bytes(data, filename)

    # Emit Prometheus metrics
    _emit_scan_metrics(result, result.threat_name)

    # Log infected files to quarantine table
    if result.status == ScanStatus.INFECTED and user_id:
        file_hash = compute_file_hash(data)
        log_quarantine(
            user_id=user_id,
            file_hash=file_hash,
            threat_name=result.threat_name or "unknown",
            original_filename=filename,
            file_size_bytes=len(data),
            content_type=content_type,
            scan_duration_ms=result.scan_duration_ms,
            source_ip=source_ip,
            user_agent=user_agent,
        )

    if result.status == ScanStatus.ERROR:
        if is_required:
            raise ClamAVError(f"Scan required but failed: {result.error_message}")

        # Log as pending scan for later when ClamAV becomes available
        if user_id and file_key:
            file_hash = compute_file_hash(data)
            log_pending_scan(
                file_key=file_key,
                user_id=user_id,
                file_hash=file_hash,
                original_filename=filename,
                file_size_bytes=len(data),
                content_type=content_type,
                source_ip=source_ip,
                user_agent=user_agent,
            )
            logger.warning(f"ClamAV unavailable for {filename}, marked as pending scan")
        else:
            logger.warning(
                f"ClamAV unavailable for {filename}, no file_key provided - cannot queue for later scan"
            )

        return ScanResult(status=ScanStatus.PENDING, scan_duration_ms=result.scan_duration_ms)

    return result
