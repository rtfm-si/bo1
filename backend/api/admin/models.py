"""Pydantic models for admin API endpoints."""

from typing import Any

from pydantic import BaseModel, Field

# ==============================================================================
# User Management Models
# ==============================================================================


class UserInfo(BaseModel):
    """Information about a user.

    Attributes:
        user_id: User identifier
        email: User email address
        auth_provider: Authentication provider (google, github, supertokens, etc.)
        subscription_tier: Subscription tier (free, pro, enterprise)
        is_admin: Whether user has admin privileges
        is_locked: Whether account is locked
        locked_at: When account was locked
        lock_reason: Reason for locking
        deleted_at: When account was soft deleted
        total_meetings: Total number of meetings created
        total_cost: Total cost across all meetings (USD)
        last_meeting_at: When user's most recent meeting was created
        last_meeting_id: ID of user's most recent meeting
        created_at: When user account was created
        updated_at: When user account was last updated
    """

    user_id: str = Field(..., description="User identifier", examples=["user_123"])
    email: str = Field(..., description="User email address", examples=["alice@example.com"])
    auth_provider: str = Field(
        ..., description="Authentication provider", examples=["google", "github", "supertokens"]
    )
    subscription_tier: str = Field(
        ..., description="Subscription tier", examples=["free", "pro", "enterprise"]
    )
    is_admin: bool = Field(..., description="Whether user has admin privileges", examples=[False])
    is_locked: bool = Field(False, description="Whether account is locked", examples=[False])
    locked_at: str | None = Field(None, description="When account was locked (ISO 8601)")
    lock_reason: str | None = Field(None, description="Reason for locking")
    deleted_at: str | None = Field(None, description="When account was soft deleted (ISO 8601)")
    total_meetings: int = Field(..., description="Total number of meetings created", examples=[5])
    total_cost: float | None = Field(
        None, description="Total cost across all meetings (USD)", examples=[0.42]
    )
    last_meeting_at: str | None = Field(
        None,
        description="When user's most recent meeting was created (ISO 8601)",
        examples=["2025-01-15T12:00:00"],
    )
    last_meeting_id: str | None = Field(
        None, description="ID of user's most recent meeting", examples=["bo1_abc123"]
    )
    created_at: str = Field(
        ...,
        description="When user account was created (ISO 8601)",
        examples=["2025-01-01T10:00:00"],
    )
    updated_at: str = Field(
        ...,
        description="When user account was last updated (ISO 8601)",
        examples=["2025-01-15T10:00:00"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user_123",
                    "email": "alice@example.com",
                    "auth_provider": "google",
                    "subscription_tier": "free",
                    "is_admin": False,
                    "total_meetings": 5,
                    "total_cost": 0.42,
                    "last_meeting_at": "2025-01-15T12:00:00",
                    "last_meeting_id": "bo1_abc123",
                    "created_at": "2025-01-01T10:00:00",
                    "updated_at": "2025-01-15T10:00:00",
                }
            ]
        }
    }


class UserListResponse(BaseModel):
    """Response model for user list.

    Attributes:
        total_count: Total number of users
        users: List of user info
        page: Current page number
        per_page: Number of users per page
    """

    total_count: int = Field(..., description="Total number of users", examples=[100])
    users: list[UserInfo] = Field(..., description="List of user info")
    page: int = Field(..., description="Current page number", examples=[1])
    per_page: int = Field(..., description="Number of users per page", examples=[10])


class UpdateUserRequest(BaseModel):
    """Request model for updating user.

    Attributes:
        subscription_tier: New subscription tier (optional)
        is_admin: New admin status (optional)
    """

    subscription_tier: str | None = Field(
        None,
        description="New subscription tier",
        examples=["free", "pro", "enterprise"],
    )
    is_admin: bool | None = Field(None, description="New admin status", examples=[True, False])


class LockUserRequest(BaseModel):
    """Request model for locking a user account.

    Attributes:
        reason: Optional reason for locking the account
    """

    reason: str | None = Field(
        None,
        description="Reason for locking the account",
        max_length=500,
        examples=["Suspicious activity", "Payment issue"],
    )


class LockUserResponse(BaseModel):
    """Response model for lock/unlock operations.

    Attributes:
        user_id: User identifier
        is_locked: Current lock status
        locked_at: When account was locked (null if unlocked)
        lock_reason: Reason for locking (null if unlocked)
        sessions_revoked: Number of sessions revoked
        message: Human-readable message
    """

    user_id: str = Field(..., description="User identifier")
    is_locked: bool = Field(..., description="Current lock status")
    locked_at: str | None = Field(None, description="When account was locked")
    lock_reason: str | None = Field(None, description="Reason for locking")
    sessions_revoked: int = Field(0, description="Number of sessions revoked")
    message: str = Field(..., description="Human-readable message")


class DeleteUserRequest(BaseModel):
    """Request model for deleting a user account.

    Attributes:
        hard_delete: If true, permanently delete (cannot be undone)
        revoke_sessions: Revoke all active SuperTokens sessions
    """

    hard_delete: bool = Field(
        False,
        description="If true, permanently delete all user data (cannot be undone)",
    )
    revoke_sessions: bool = Field(
        True,
        description="Revoke all active SuperTokens sessions",
    )


class DeleteUserResponse(BaseModel):
    """Response model for user deletion.

    Attributes:
        user_id: User identifier
        deleted: Whether deletion was successful
        hard_delete: Whether this was a permanent deletion
        sessions_revoked: Number of sessions revoked
        message: Human-readable message
    """

    user_id: str = Field(..., description="User identifier")
    deleted: bool = Field(..., description="Whether deletion was successful")
    hard_delete: bool = Field(..., description="Whether this was a permanent deletion")
    sessions_revoked: int = Field(0, description="Number of sessions revoked")
    message: str = Field(..., description="Human-readable message")


class AdminStatsResponse(BaseModel):
    """Response model for admin dashboard statistics.

    Attributes:
        total_users: Total number of registered users
        total_meetings: Total number of meetings across all users
        total_cost: Total cost across all users (USD)
        whitelist_count: Number of whitelisted emails
        waitlist_pending: Number of pending waitlist entries
    """

    total_users: int = Field(..., description="Total number of registered users")
    total_meetings: int = Field(..., description="Total number of meetings across all users")
    total_cost: float = Field(..., description="Total cost across all users (USD)")
    whitelist_count: int = Field(..., description="Number of whitelisted emails")
    waitlist_pending: int = Field(..., description="Number of pending waitlist entries")


class SetTierOverrideRequest(BaseModel):
    """Request model for setting tier override.

    Attributes:
        tier: Override tier (free, starter, pro, enterprise)
        expires_at: When override expires (ISO 8601, optional - null means no expiry)
        reason: Reason for override (e.g., "beta tester", "goodwill credit")
    """

    tier: str = Field(
        ...,
        description="Override tier",
        examples=["pro", "starter", "enterprise"],
    )
    expires_at: str | None = Field(
        None,
        description="When override expires (ISO 8601). Null means no expiry.",
        examples=["2025-06-01T00:00:00Z"],
    )
    reason: str = Field(
        ...,
        description="Reason for override",
        max_length=200,
        examples=["Beta tester", "Goodwill credit", "Conference demo"],
    )


class TierOverrideResponse(BaseModel):
    """Response model for tier override operations.

    Attributes:
        user_id: User identifier
        tier_override: Current override (null if none)
        effective_tier: Effective tier after considering override
        message: Human-readable message
    """

    user_id: str = Field(..., description="User identifier")
    tier_override: dict[str, Any] | None = Field(None, description="Current override settings")
    effective_tier: str = Field(..., description="Effective tier after considering override")
    message: str = Field(..., description="Human-readable message")


# ==============================================================================
# Session Management Models
# ==============================================================================


class ActiveSessionInfo(BaseModel):
    """Information about an active session.

    Attributes:
        session_id: Session identifier
        user_id: User who owns the session
        status: Current session status
        phase: Current deliberation phase
        started_at: When session started
        duration_seconds: How long session has been running
        cost: Total cost so far
    """

    session_id: str = Field(
        ..., description="Session identifier", examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    user_id: str = Field(..., description="User who owns the session", examples=["test_user_1"])
    status: str = Field(..., description="Current session status", examples=["active", "running"])
    phase: str | None = Field(
        None, description="Current deliberation phase", examples=["discussion", "voting"]
    )
    started_at: str = Field(
        ..., description="When session started (ISO 8601)", examples=["2025-01-15T12:00:00"]
    )
    duration_seconds: float = Field(
        ..., description="How long session has been running", examples=[120.5]
    )
    cost: float | None = Field(None, description="Total cost so far (USD)", examples=[0.0145])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "test_user_1",
                    "status": "running",
                    "phase": "discussion",
                    "started_at": "2025-01-15T12:00:00",
                    "duration_seconds": 120.5,
                    "cost": 0.0145,
                }
            ]
        }
    }


class ActiveSessionsResponse(BaseModel):
    """Response model for active sessions list.

    Attributes:
        active_count: Number of active sessions
        sessions: List of active session info
        longest_running: Top N longest running sessions
        most_expensive: Top N most expensive sessions
    """

    active_count: int = Field(..., description="Number of active sessions", examples=[3])
    sessions: list[ActiveSessionInfo] = Field(..., description="List of active sessions")
    longest_running: list[ActiveSessionInfo] = Field(
        ..., description="Top N longest running sessions"
    )
    most_expensive: list[ActiveSessionInfo] = Field(
        ..., description="Top N most expensive sessions"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "active_count": 3,
                    "sessions": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                    "longest_running": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                    "most_expensive": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                }
            ]
        }
    }


class FullSessionResponse(BaseModel):
    """Response model for full session details.

    Attributes:
        session_id: Session identifier
        metadata: Full session metadata
        state: Full deliberation state
        is_active: Whether session is currently running
    """

    session_id: str = Field(..., description="Session identifier")
    metadata: dict[str, Any] = Field(..., description="Full session metadata")
    state: dict[str, Any] | None = Field(None, description="Full deliberation state")
    is_active: bool = Field(..., description="Whether session is currently running")


class KillAllResponse(BaseModel):
    """Response model for kill-all operation.

    Attributes:
        killed_count: Number of sessions killed
        message: Human-readable message
    """

    killed_count: int = Field(..., description="Number of sessions killed")
    message: str = Field(..., description="Human-readable message")


class SessionKillResponse(BaseModel):
    """Response model for a session kill audit record.

    Attributes:
        id: Record ID
        session_id: Session that was killed (may be null if session deleted)
        killed_by: Who killed the session (user_id or 'system')
        reason: Reason for the kill
        cost_at_kill: Session cost at time of kill (USD)
        created_at: When the kill occurred
    """

    id: int = Field(..., description="Record ID")
    session_id: str | None = Field(None, description="Session that was killed")
    killed_by: str = Field(..., description="Who killed the session")
    reason: str = Field(..., description="Reason for the kill")
    cost_at_kill: float | None = Field(None, description="Session cost at kill (USD)")
    created_at: str = Field(..., description="When the kill occurred (ISO 8601)")


class SessionKillsResponse(BaseModel):
    """Response model for session kill history.

    Attributes:
        total: Total number of kill records
        kills: List of kill records
        limit: Max records returned
        offset: Records skipped
    """

    total: int = Field(..., description="Total number of kill records")
    kills: list[SessionKillResponse] = Field(..., description="List of kill records")
    limit: int = Field(..., description="Max records returned")
    offset: int = Field(..., description="Records skipped")


# ==============================================================================
# Research Cache Models
# ==============================================================================


class ResearchCacheStats(BaseModel):
    """Response model for research cache statistics.

    Attributes:
        total_cached_results: Total number of cached research results
        cache_hit_rate_30d: Cache hit rate in last 30 days (percentage)
        cost_savings_30d: Cost savings in last 30 days (USD)
        top_cached_questions: Top 10 most accessed cached questions
    """

    total_cached_results: int = Field(..., description="Total number of cached research results")
    cache_hit_rate_30d: float = Field(
        ..., description="Cache hit rate in last 30 days (percentage)"
    )
    cost_savings_30d: float = Field(..., description="Cost savings in last 30 days (USD)")
    top_cached_questions: list[dict[str, Any]] = Field(
        ..., description="Top 10 most accessed cached questions"
    )


class StaleEntriesResponse(BaseModel):
    """Response model for stale cache entries.

    Attributes:
        stale_count: Number of stale entries found
        entries: List of stale cache entries
    """

    stale_count: int = Field(..., description="Number of stale entries found")
    entries: list[dict[str, Any]] = Field(..., description="List of stale cache entries")


# ==============================================================================
# Beta Whitelist Models
# ==============================================================================


class BetaWhitelistEntry(BaseModel):
    """Response model for beta whitelist entry.

    Attributes:
        id: Entry ID
        email: Whitelisted email address
        added_by: Admin who added this email
        notes: Optional notes about the beta tester
        created_at: When email was added
    """

    id: str = Field(..., description="Entry ID (UUID)")
    email: str = Field(..., description="Whitelisted email address")
    added_by: str | None = Field(None, description="Admin who added this email")
    notes: str | None = Field(None, description="Optional notes about the beta tester")
    created_at: str = Field(..., description="When email was added (ISO 8601)")


class BetaWhitelistResponse(BaseModel):
    """Response model for beta whitelist list.

    Attributes:
        total_count: Total number of whitelisted emails
        emails: List of whitelist entries from database
    """

    total_count: int = Field(..., description="Total number of whitelisted emails")
    emails: list[BetaWhitelistEntry] = Field(
        ..., description="List of whitelist entries from database"
    )


class AddWhitelistRequest(BaseModel):
    """Request model for adding email to whitelist.

    Attributes:
        email: Email address to whitelist
        notes: Optional notes about the beta tester
    """

    email: str = Field(
        ..., description="Email address to whitelist", examples=["alice@example.com"]
    )
    notes: str | None = Field(
        None,
        description="Optional notes about the beta tester",
        examples=["YC batch W25", "Referred by Alice"],
    )


# ==============================================================================
# Waitlist Models
# ==============================================================================


class WaitlistEntry(BaseModel):
    """Response model for waitlist entry.

    Attributes:
        id: Entry ID
        email: Email address
        status: Status (pending, invited, converted)
        source: Where they signed up from
        notes: Admin notes
        created_at: When they joined the waitlist
    """

    id: str = Field(..., description="Entry ID (UUID)")
    email: str = Field(..., description="Email address")
    status: str = Field(..., description="Status: pending, invited, converted")
    source: str | None = Field(None, description="Signup source")
    notes: str | None = Field(None, description="Admin notes")
    created_at: str = Field(..., description="When they joined (ISO 8601)")


class WaitlistResponse(BaseModel):
    """Response model for waitlist list.

    Attributes:
        total_count: Total number of waitlist entries
        pending_count: Number of pending entries
        entries: List of waitlist entries
    """

    total_count: int = Field(..., description="Total number of waitlist entries")
    pending_count: int = Field(..., description="Number of pending entries")
    entries: list[WaitlistEntry] = Field(..., description="List of waitlist entries")


class ApproveWaitlistResponse(BaseModel):
    """Response model for waitlist approval.

    Attributes:
        email: Approved email address
        whitelist_added: Whether email was added to whitelist
        email_sent: Whether welcome email was sent
        message: Human-readable message
    """

    email: str = Field(..., description="Approved email address")
    whitelist_added: bool = Field(..., description="Whether added to whitelist")
    email_sent: bool = Field(..., description="Whether welcome email was sent")
    message: str = Field(..., description="Human-readable message")


# ==============================================================================
# Alert History Models
# ==============================================================================


class AlertHistoryItem(BaseModel):
    """Response model for a single alert history entry.

    Attributes:
        id: Alert ID
        alert_type: Type of alert (e.g., runaway_session, auth_failure_spike)
        severity: Alert severity (info, warning, high, urgent, critical)
        title: Alert title
        message: Alert message body
        metadata: Additional context (session_id, user_id, IP, etc.)
        delivered: Whether ntfy delivery succeeded
        created_at: When alert was created
    """

    id: int = Field(..., description="Alert ID")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    metadata: dict[str, Any] | None = Field(None, description="Additional context")
    delivered: bool = Field(..., description="Whether ntfy delivery succeeded")
    created_at: str = Field(..., description="When alert was created (ISO 8601)")


class AlertHistoryResponse(BaseModel):
    """Response model for paginated alert history.

    Attributes:
        total: Total number of alerts
        alerts: List of alert entries
        limit: Max records returned
        offset: Records skipped
    """

    total: int = Field(..., description="Total number of alerts")
    alerts: list[AlertHistoryItem] = Field(..., description="List of alerts")
    limit: int = Field(..., description="Max records returned")
    offset: int = Field(..., description="Records skipped")


class AlertSettingsResponse(BaseModel):
    """Response model for alert settings (thresholds).

    All thresholds are read from bo1/constants.py (SecurityAlerts class).
    Settings are read-only from environment/constants.

    Attributes:
        auth_failure_threshold: Failures before auth spike alert
        auth_failure_window_minutes: Window for auth failure detection
        rate_limit_threshold: Hits before rate limit spike alert
        rate_limit_window_minutes: Window for rate limit detection
        lockout_threshold: Lockouts before lockout spike alert
    """

    auth_failure_threshold: int = Field(..., description="Auth failures before alert")
    auth_failure_window_minutes: int = Field(..., description="Auth failure window (minutes)")
    rate_limit_threshold: int = Field(..., description="Rate limit hits before alert")
    rate_limit_window_minutes: int = Field(..., description="Rate limit window (minutes)")
    lockout_threshold: int = Field(..., description="Lockouts before alert")


# ==============================================================================
# Admin Impersonation Models
# ==============================================================================


class StartImpersonationRequest(BaseModel):
    """Request model for starting an impersonation session.

    Attributes:
        reason: Reason for impersonation (for audit)
        write_mode: Allow mutations if True (default: read-only)
        duration_minutes: Session duration (default: 30, max: 60)
    """

    reason: str = Field(
        ...,
        description="Reason for impersonation (required for audit trail)",
        min_length=5,
        max_length=500,
        examples=["Investigating user-reported bug in action creation"],
    )
    write_mode: bool = Field(
        False,
        description="Allow mutations (POST/PUT/PATCH/DELETE). Default: read-only",
    )
    duration_minutes: int = Field(
        30,
        ge=5,
        le=60,
        description="Session duration in minutes (5-60)",
    )


class ImpersonationSessionResponse(BaseModel):
    """Response model for impersonation session data.

    Attributes:
        admin_user_id: Admin user performing impersonation
        target_user_id: User being impersonated
        target_email: Email of target user
        reason: Reason for impersonation
        is_write_mode: Whether mutations are allowed
        started_at: When session started
        expires_at: When session expires
        remaining_seconds: Seconds until expiry
    """

    admin_user_id: str = Field(..., description="Admin user ID")
    target_user_id: str = Field(..., description="Target user ID")
    target_email: str | None = Field(None, description="Target user email")
    reason: str = Field(..., description="Reason for impersonation")
    is_write_mode: bool = Field(..., description="Whether mutations allowed")
    started_at: str = Field(..., description="Session start time (ISO 8601)")
    expires_at: str = Field(..., description="Session expiry time (ISO 8601)")
    remaining_seconds: int = Field(..., description="Seconds until expiry")


class ImpersonationStatusResponse(BaseModel):
    """Response model for impersonation status check.

    Attributes:
        is_impersonating: Whether admin is currently impersonating
        session: Active session details (if impersonating)
    """

    is_impersonating: bool = Field(..., description="Whether currently impersonating")
    session: ImpersonationSessionResponse | None = Field(
        None, description="Active session (if impersonating)"
    )


class EndImpersonationResponse(BaseModel):
    """Response model for ending impersonation.

    Attributes:
        ended: Whether session was ended
        message: Human-readable message
    """

    ended: bool = Field(..., description="Whether session was ended")
    message: str = Field(..., description="Human-readable message")


class ImpersonationHistoryItem(BaseModel):
    """Response model for impersonation history entry.

    Attributes:
        id: Session record ID
        admin_user_id: Admin user ID
        admin_email: Admin user email
        target_user_id: Target user ID
        target_email: Target user email
        reason: Reason for impersonation
        is_write_mode: Whether mutations were allowed
        started_at: When session started
        expires_at: When session was set to expire
        ended_at: When session actually ended (null if expired)
    """

    id: int = Field(..., description="Session record ID")
    admin_user_id: str = Field(..., description="Admin user ID")
    admin_email: str = Field(..., description="Admin user email")
    target_user_id: str = Field(..., description="Target user ID")
    target_email: str = Field(..., description="Target user email")
    reason: str = Field(..., description="Reason for impersonation")
    is_write_mode: bool = Field(..., description="Whether mutations allowed")
    started_at: str = Field(..., description="Session start time (ISO 8601)")
    expires_at: str = Field(..., description="Session expiry time (ISO 8601)")
    ended_at: str | None = Field(None, description="Session end time (ISO 8601)")


class ImpersonationHistoryResponse(BaseModel):
    """Response model for impersonation history.

    Attributes:
        total: Total number of records
        sessions: List of history entries
        limit: Max records returned
    """

    total: int = Field(..., description="Total records")
    sessions: list[ImpersonationHistoryItem] = Field(..., description="History entries")
    limit: int = Field(..., description="Max records returned")
