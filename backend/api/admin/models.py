"""Pydantic models for admin API endpoints."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ==============================================================================
# Common Enums
# ==============================================================================


class TimePeriod(str, Enum):
    """Time period for drill-down filtering."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


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
        is_nonprofit: Whether user is verified nonprofit
        nonprofit_org_name: Name of nonprofit organization
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
    is_nonprofit: bool = Field(False, description="Whether user is verified nonprofit")
    nonprofit_org_name: str | None = Field(None, description="Name of nonprofit organization")
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
        has_more: Whether more users exist beyond current page
        next_offset: Offset for next page (None if no more pages)
    """

    total_count: int = Field(..., description="Total number of users", examples=[100])
    users: list[UserInfo] = Field(..., description="List of user info")
    page: int = Field(..., description="Current page number", examples=[1])
    per_page: int = Field(..., description="Number of users per page", examples=[10])
    has_more: bool = Field(..., description="Whether more users exist beyond current page")
    next_offset: int | None = Field(None, description="Offset for next page (None if no more)")


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
        updated_at: When the record was last updated
    """

    id: int = Field(..., description="Record ID")
    session_id: str | None = Field(None, description="Session that was killed")
    killed_by: str = Field(..., description="Who killed the session")
    reason: str = Field(..., description="Reason for the kill")
    cost_at_kill: float | None = Field(None, description="Session cost at kill (USD)")
    created_at: str = Field(..., description="When the kill occurred (ISO 8601)")
    updated_at: str | None = Field(None, description="When record was last updated (ISO 8601)")


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


class SimilarityBucket(BaseModel):
    """A bucket in the similarity distribution histogram.

    Attributes:
        bucket: Bucket number (1-5)
        range_start: Start of similarity range
        range_end: End of similarity range
        count: Number of entries in this bucket
    """

    bucket: int = Field(..., description="Bucket number (1-5)")
    range_start: float = Field(..., description="Start of similarity range")
    range_end: float = Field(..., description="End of similarity range")
    count: int = Field(..., description="Number of entries in this bucket")


class CacheMetricsResponse(BaseModel):
    """Response model for detailed research cache metrics.

    Provides multi-period hit rates, miss distribution, and threshold recommendations.

    Attributes:
        hit_rate_1d: Cache hit rate in last 24 hours (percentage)
        hit_rate_7d: Cache hit rate in last 7 days (percentage)
        hit_rate_30d: Cache hit rate in last 30 days (percentage)
        total_queries_1d: Total research queries in last 24 hours
        total_queries_7d: Total research queries in last 7 days
        total_queries_30d: Total research queries in last 30 days
        cache_hits_1d: Cache hits in last 24 hours
        cache_hits_7d: Cache hits in last 7 days
        cache_hits_30d: Cache hits in last 30 days
        avg_similarity_on_hit: Mean similarity score for cache hits
        miss_distribution: Histogram of near-miss similarity scores (0.70-0.85)
        current_threshold: Current similarity threshold from config
        recommended_threshold: Algorithm-suggested threshold
        recommendation_reason: Explanation for recommendation
        recommendation_confidence: Confidence level (low, medium, high)
        total_cached_results: Total entries in cache
        cost_savings_30d: Estimated cost savings in last 30 days (USD)
    """

    hit_rate_1d: float = Field(..., description="Cache hit rate in last 24 hours (%)")
    hit_rate_7d: float = Field(..., description="Cache hit rate in last 7 days (%)")
    hit_rate_30d: float = Field(..., description="Cache hit rate in last 30 days (%)")
    total_queries_1d: int = Field(..., description="Total queries in last 24 hours")
    total_queries_7d: int = Field(..., description="Total queries in last 7 days")
    total_queries_30d: int = Field(..., description="Total queries in last 30 days")
    cache_hits_1d: int = Field(..., description="Cache hits in last 24 hours")
    cache_hits_7d: int = Field(..., description="Cache hits in last 7 days")
    cache_hits_30d: int = Field(..., description="Cache hits in last 30 days")
    avg_similarity_on_hit: float = Field(..., description="Mean similarity score for hits")
    miss_distribution: list[SimilarityBucket] = Field(
        ..., description="Near-miss similarity distribution (0.70-0.85)"
    )
    current_threshold: float = Field(..., description="Current similarity threshold")
    recommended_threshold: float = Field(..., description="Recommended similarity threshold")
    recommendation_reason: str = Field(..., description="Explanation for recommendation")
    recommendation_confidence: str = Field(..., description="Confidence level: low, medium, high")
    total_cached_results: int = Field(..., description="Total entries in cache")
    cost_savings_30d: float = Field(..., description="Estimated savings in last 30 days (USD)")


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
        updated_at: When the record was last updated
    """

    id: int = Field(..., description="Alert ID")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    metadata: dict[str, Any] | None = Field(None, description="Additional context")
    delivered: bool = Field(..., description="Whether ntfy delivery succeeded")
    created_at: str = Field(..., description="When alert was created (ISO 8601)")
    updated_at: str | None = Field(None, description="When record was last updated (ISO 8601)")


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


# ==============================================================================
# Extended KPIs Models
# ==============================================================================


class MentorSessionStats(BaseModel):
    """Statistics for mentor chat sessions.

    Attributes:
        total_sessions: Total mentor chat sessions across all users
        sessions_today: Sessions started today
        sessions_this_week: Sessions in the last 7 days
        sessions_this_month: Sessions in the last 30 days
    """

    total_sessions: int = Field(..., description="Total mentor sessions")
    sessions_today: int = Field(0, description="Sessions today")
    sessions_this_week: int = Field(0, description="Sessions in last 7 days")
    sessions_this_month: int = Field(0, description="Sessions in last 30 days")


class DataAnalysisStats(BaseModel):
    """Statistics for dataset analyses.

    Attributes:
        total_analyses: Total dataset analyses across all users
        analyses_today: Analyses started today
        analyses_this_week: Analyses in the last 7 days
        analyses_this_month: Analyses in the last 30 days
    """

    total_analyses: int = Field(..., description="Total dataset analyses")
    analyses_today: int = Field(0, description="Analyses today")
    analyses_this_week: int = Field(0, description="Analyses in last 7 days")
    analyses_this_month: int = Field(0, description="Analyses in last 30 days")


class ProjectStats(BaseModel):
    """Statistics for projects by status.

    Attributes:
        total_projects: Total projects across all users
        active: Active projects
        paused: Paused projects
        completed: Completed projects
        archived: Archived projects
        deleted: Soft-deleted projects
    """

    total_projects: int = Field(..., description="Total projects")
    active: int = Field(0, description="Active projects")
    paused: int = Field(0, description="Paused projects")
    completed: int = Field(0, description="Completed projects")
    archived: int = Field(0, description="Archived projects")
    deleted: int = Field(0, description="Deleted projects")


class ActionStats(BaseModel):
    """Statistics for actions by status.

    Attributes:
        total_actions: Total actions across all users
        pending: Pending actions
        in_progress: In-progress actions
        completed: Completed actions
        cancelled: Cancelled actions
        deleted: Soft-deleted actions
    """

    total_actions: int = Field(..., description="Total actions")
    pending: int = Field(0, description="Pending actions")
    in_progress: int = Field(0, description="In-progress actions")
    completed: int = Field(0, description="Completed actions")
    cancelled: int = Field(0, description="Cancelled actions")
    deleted: int = Field(0, description="Deleted actions")


class MeetingStats(BaseModel):
    """Statistics for meetings/sessions by status.

    Attributes:
        total_meetings: Total meetings across all users
        created: Meetings with status 'created'
        running: Currently running meetings
        completed: Successfully completed meetings
        failed: Failed meetings
        killed: Killed meetings
        deleted: Soft-deleted meetings
        meetings_today: Meetings created today
        meetings_this_week: Meetings in the last 7 days
        meetings_this_month: Meetings in the last 30 days
    """

    total_meetings: int = Field(..., description="Total meetings")
    created: int = Field(0, description="Created meetings")
    running: int = Field(0, description="Running meetings")
    completed: int = Field(0, description="Completed meetings")
    failed: int = Field(0, description="Failed meetings")
    killed: int = Field(0, description="Killed meetings")
    deleted: int = Field(0, description="Deleted meetings")
    meetings_today: int = Field(0, description="Meetings today")
    meetings_this_week: int = Field(0, description="Meetings in last 7 days")
    meetings_this_month: int = Field(0, description="Meetings in last 30 days")


class ExtendedKPIsResponse(BaseModel):
    """Response model for extended KPIs.

    Attributes:
        mentor_sessions: Mentor session statistics
        data_analyses: Dataset analysis statistics
        projects: Project statistics by status
        actions: Action statistics by status
        meetings: Meeting/session statistics by status
    """

    mentor_sessions: MentorSessionStats = Field(..., description="Mentor session stats")
    data_analyses: DataAnalysisStats = Field(..., description="Dataset analysis stats")
    projects: ProjectStats = Field(..., description="Project stats by status")
    actions: ActionStats = Field(..., description="Action stats by status")
    meetings: MeetingStats = Field(..., description="Meeting stats by status")


# ==============================================================================
# Cost Tracking Models
# ==============================================================================


class FixedCostItem(BaseModel):
    """Fixed infrastructure cost entry."""

    id: int
    provider: str
    description: str
    monthly_amount_usd: float
    category: str
    active: bool
    notes: str | None = None


class FixedCostsResponse(BaseModel):
    """Response with list of fixed costs."""

    costs: list[FixedCostItem]
    monthly_total: float


class CreateFixedCostRequest(BaseModel):
    """Request to create a fixed cost entry."""

    provider: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=200)
    monthly_amount_usd: float = Field(..., ge=0)
    category: str = Field(default="compute", max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class UpdateFixedCostRequest(BaseModel):
    """Request to update a fixed cost entry."""

    monthly_amount_usd: float | None = Field(default=None, ge=0)
    active: bool | None = None
    notes: str | None = None


class ProviderCostItem(BaseModel):
    """Cost breakdown for a single provider."""

    provider: str
    amount_usd: float
    request_count: int
    percentage: float


class CostsByProviderResponse(BaseModel):
    """Response with costs grouped by provider."""

    providers: list[ProviderCostItem]
    total_usd: float
    period_start: str
    period_end: str


class MeetingCostResponse(BaseModel):
    """Cost breakdown for a single meeting/session."""

    session_id: str
    total_cost: float
    api_calls: int
    by_provider: dict[str, float]
    by_phase: dict[str, float]


class PerUserCostItem(BaseModel):
    """Per-user cost metrics."""

    user_id: str
    email: str | None
    total_cost: float
    session_count: int
    avg_cost_per_session: float


class PerUserCostResponse(BaseModel):
    """Response with average cost per user."""

    users: list[PerUserCostItem]
    overall_avg: float
    total_users: int
    period_start: str
    period_end: str


class DailySummaryItem(BaseModel):
    """Single day cost summary."""

    date: str
    total_usd: float
    by_provider: dict[str, float]
    request_count: int


class DailySummaryResponse(BaseModel):
    """Response with daily cost summaries."""

    days: list[DailySummaryItem]
    period_start: str
    period_end: str


# ==============================================================================
# Drill-Down Models
# ==============================================================================


class UserDrillDownItem(BaseModel):
    """Single user item in drill-down list.

    Attributes:
        user_id: User identifier
        email: User email
        subscription_tier: Subscription tier
        is_admin: Whether user is admin
        created_at: When user was created (ISO 8601)
    """

    user_id: str = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    subscription_tier: str = Field(..., description="Subscription tier")
    is_admin: bool = Field(..., description="Whether user is admin")
    created_at: str = Field(..., description="When user was created (ISO 8601)")


class UserDrillDownResponse(BaseModel):
    """Response for user drill-down list.

    Attributes:
        items: List of user items
        total: Total count matching filter
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
        period: Time period filter applied
    """

    items: list[UserDrillDownItem] = Field(..., description="List of users")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")
    period: str = Field(..., description="Time period filter applied")


class CostDrillDownItem(BaseModel):
    """Single cost record in drill-down list.

    Attributes:
        id: Cost record ID
        user_id: User who incurred cost
        email: User email (if available)
        provider: LLM provider
        model: Model name
        amount_usd: Cost in USD
        created_at: When cost was recorded (ISO 8601)
    """

    id: int = Field(..., description="Cost record ID")
    user_id: str = Field(..., description="User identifier")
    email: str | None = Field(None, description="User email")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    amount_usd: float = Field(..., description="Cost in USD")
    created_at: str = Field(..., description="When cost was recorded (ISO 8601)")


class CostDrillDownResponse(BaseModel):
    """Response for cost drill-down list.

    Attributes:
        items: List of cost items
        total: Total count matching filter
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
        period: Time period filter applied
        total_cost_usd: Sum of costs in period
    """

    items: list[CostDrillDownItem] = Field(..., description="List of cost records")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")
    period: str = Field(..., description="Time period filter applied")
    total_cost_usd: float = Field(..., description="Sum of costs in period")


class WaitlistDrillDownItem(BaseModel):
    """Single waitlist entry in drill-down list.

    Attributes:
        id: Entry ID
        email: Email address
        status: Status (pending, invited, converted)
        source: Signup source
        created_at: When added to waitlist (ISO 8601)
    """

    id: str = Field(..., description="Entry ID")
    email: str = Field(..., description="Email address")
    status: str = Field(..., description="Status")
    source: str | None = Field(None, description="Signup source")
    created_at: str = Field(..., description="When added (ISO 8601)")


class WaitlistDrillDownResponse(BaseModel):
    """Response for waitlist drill-down list.

    Attributes:
        items: List of waitlist entries
        total: Total count matching filter
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
        period: Time period filter applied
    """

    items: list[WaitlistDrillDownItem] = Field(..., description="List of waitlist entries")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")
    period: str = Field(..., description="Time period filter applied")


class WhitelistDrillDownItem(BaseModel):
    """Single whitelist entry in drill-down list.

    Attributes:
        id: Entry ID
        email: Whitelisted email
        added_by: Admin who added
        notes: Optional notes
        created_at: When added (ISO 8601)
    """

    id: str = Field(..., description="Entry ID")
    email: str = Field(..., description="Email address")
    added_by: str | None = Field(None, description="Admin who added")
    notes: str | None = Field(None, description="Notes")
    created_at: str = Field(..., description="When added (ISO 8601)")


class WhitelistDrillDownResponse(BaseModel):
    """Response for whitelist drill-down list.

    Attributes:
        items: List of whitelist entries
        total: Total count matching filter
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
        period: Time period filter applied
    """

    items: list[WhitelistDrillDownItem] = Field(..., description="List of whitelist entries")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")
    period: str = Field(..., description="Time period filter applied")


# ==============================================================================
# Research Costs Models
# ==============================================================================


class ResearchCostItem(BaseModel):
    """Cost data for a single research provider.

    Attributes:
        provider: Research provider name (brave, tavily)
        amount_usd: Total cost in USD
        query_count: Number of API calls made
    """

    provider: str = Field(..., description="Research provider (brave, tavily)")
    amount_usd: float = Field(..., description="Total cost in USD")
    query_count: int = Field(..., description="Number of queries/calls")


class ResearchCostsByPeriod(BaseModel):
    """Research costs aggregated by time period.

    Attributes:
        today: Costs from today
        week: Costs from last 7 days
        month: Costs from last 30 days
        all_time: All-time costs
    """

    today: float = Field(0.0, description="Cost today (USD)")
    week: float = Field(0.0, description="Cost this week (USD)")
    month: float = Field(0.0, description="Cost this month (USD)")
    all_time: float = Field(0.0, description="All-time cost (USD)")


class DailyResearchCost(BaseModel):
    """Daily research cost for trend chart.

    Attributes:
        date: Date (YYYY-MM-DD)
        brave: Brave costs for the day
        tavily: Tavily costs for the day
        total: Total costs for the day
    """

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    brave: float = Field(0.0, description="Brave costs (USD)")
    tavily: float = Field(0.0, description="Tavily costs (USD)")
    total: float = Field(0.0, description="Total costs (USD)")


class ResearchCostsResponse(BaseModel):
    """Response model for research costs endpoint.

    Attributes:
        brave: Brave Search costs breakdown
        tavily: Tavily costs breakdown
        total_usd: Total research costs
        total_queries: Total number of research queries
        by_period: Costs aggregated by time period
        daily_trend: Last 7 days of costs for chart
    """

    brave: ResearchCostItem = Field(..., description="Brave Search costs")
    tavily: ResearchCostItem = Field(..., description="Tavily costs")
    total_usd: float = Field(..., description="Total research costs (USD)")
    total_queries: int = Field(..., description="Total research queries")
    by_period: ResearchCostsByPeriod = Field(..., description="Costs by time period")
    daily_trend: list[DailyResearchCost] = Field(..., description="Daily costs for chart")


# ==============================================================================
# Terms & Conditions Consent Audit Models
# ==============================================================================


class ConsentAuditItem(BaseModel):
    """Single consent audit entry.

    Attributes:
        user_id: User identifier
        email: User email (if available)
        terms_version: T&C version string (e.g., "1.0")
        consented_at: When consent was given (ISO 8601)
        ip_address: IP address at time of consent
    """

    user_id: str = Field(..., description="User identifier")
    email: str | None = Field(None, description="User email")
    terms_version: str = Field(..., description="T&C version string")
    consented_at: str = Field(..., description="When consent was given (ISO 8601)")
    ip_address: str | None = Field(None, description="IP address at consent")


class ConsentAuditResponse(BaseModel):
    """Response for consent audit list.

    Attributes:
        items: List of consent entries
        total: Total count matching filter
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
        period: Time period filter applied
    """

    items: list[ConsentAuditItem] = Field(..., description="List of consent entries")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")
    period: str = Field(..., description="Time period filter applied")


# ==============================================================================
# Terms Version Management Models
# ==============================================================================


class TermsVersionItem(BaseModel):
    """Single T&C version entry.

    Attributes:
        id: Version UUID
        version: Version string (e.g., "1.0")
        content: T&C content (markdown)
        is_active: Whether this is the active version
        published_at: When version was published (ISO 8601, null if draft)
        created_at: When version was created (ISO 8601)
    """

    id: str = Field(..., description="Version UUID")
    version: str = Field(..., description="Version string (e.g., '1.0')")
    content: str = Field(..., description="T&C content (markdown)")
    is_active: bool = Field(..., description="Whether this is the active version")
    published_at: str | None = Field(None, description="When published (ISO 8601)")
    created_at: str = Field(..., description="When created (ISO 8601)")


class TermsVersionListResponse(BaseModel):
    """Response for terms version list.

    Attributes:
        items: List of version entries
        total: Total count
        limit: Page size
        offset: Current offset
        has_more: Whether more items exist
        next_offset: Offset for next page
    """

    items: list[TermsVersionItem] = Field(..., description="List of versions")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: int | None = Field(None, description="Offset for next page")


class CreateTermsVersionRequest(BaseModel):
    """Request to create a new T&C version.

    Attributes:
        version: Version string (e.g., "1.1")
        content: T&C content (markdown)
    """

    version: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Version string",
        examples=["1.1", "2.0"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="T&C content (markdown)",
    )


class UpdateTermsVersionRequest(BaseModel):
    """Request to update a draft T&C version.

    Attributes:
        content: Updated T&C content (markdown)
    """

    content: str = Field(
        ...,
        min_length=1,
        description="Updated T&C content (markdown)",
    )


# ==============================================================================
# A/B Experiment Models
# ==============================================================================


class ExperimentVariantStats(BaseModel):
    """Statistics for a single A/B test variant.

    Attributes:
        variant: Variant value (e.g., 3 or 5 for persona count)
        session_count: Number of sessions with this variant
        completed_count: Number of completed sessions
        avg_cost: Average total cost per session (USD)
        avg_duration_seconds: Average session duration
        avg_rounds: Average number of rounds
        avg_persona_count: Actual average personas selected
        completion_rate: Percentage of sessions completed successfully
    """

    variant: int = Field(..., description="Variant value (3 or 5)")
    session_count: int = Field(..., description="Total sessions with this variant")
    completed_count: int = Field(..., description="Completed sessions")
    avg_cost: float | None = Field(None, description="Average cost per session (USD)")
    avg_duration_seconds: float | None = Field(None, description="Average duration (s)")
    avg_rounds: float | None = Field(None, description="Average number of rounds")
    avg_persona_count: float | None = Field(None, description="Average personas selected")
    completion_rate: float = Field(..., description="Completion rate (0-100%)")


class ExperimentMetricsResponse(BaseModel):
    """Response model for A/B experiment metrics.

    Attributes:
        experiment_name: Name of the experiment
        variants: Stats for each variant
        total_sessions: Total sessions in experiment
        period_start: Start of analysis period (ISO 8601)
        period_end: End of analysis period (ISO 8601)
    """

    experiment_name: str = Field(..., description="Experiment name")
    variants: list[ExperimentVariantStats] = Field(..., description="Per-variant stats")
    total_sessions: int = Field(..., description="Total sessions in experiment")
    period_start: str = Field(..., description="Analysis period start (ISO 8601)")
    period_end: str = Field(..., description="Analysis period end (ISO 8601)")


# ==============================================================================
# Nonprofit Status Models
# ==============================================================================


class SetNonprofitRequest(BaseModel):
    """Request model for setting nonprofit status.

    Attributes:
        org_name: Name of the nonprofit organization
        apply_promo_code: Optional promo code to auto-apply (NONPROFIT80 or NONPROFIT100)
    """

    org_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the nonprofit organization",
        examples=["Doctors Without Borders", "Local Food Bank"],
    )
    apply_promo_code: str | None = Field(
        None,
        description="Promo code to apply (NONPROFIT80 or NONPROFIT100)",
        examples=["NONPROFIT80", "NONPROFIT100"],
    )


class NonprofitStatusResponse(BaseModel):
    """Response model for nonprofit status operations.

    Attributes:
        user_id: User identifier
        is_nonprofit: Whether user is marked as nonprofit
        nonprofit_org_name: Name of the nonprofit organization
        nonprofit_verified_at: When nonprofit status was verified (ISO 8601)
        promo_applied: Whether a promo code was applied
        message: Human-readable message
    """

    user_id: str = Field(..., description="User identifier")
    is_nonprofit: bool = Field(..., description="Whether user is marked as nonprofit")
    nonprofit_org_name: str | None = Field(None, description="Nonprofit organization name")
    nonprofit_verified_at: str | None = Field(None, description="Verification date (ISO 8601)")
    promo_applied: bool = Field(False, description="Whether promo code was applied")
    message: str = Field(..., description="Human-readable message")


# ==============================================================================
# Unified Cache Metrics Models
# ==============================================================================


class CacheTypeMetrics(BaseModel):
    """Metrics for a single cache type.

    Attributes:
        hit_rate: Cache hit rate (0.0-1.0)
        hits: Total cache hits
        misses: Total cache misses
        total: Total requests
    """

    hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    hits: int = Field(..., description="Total cache hits")
    misses: int = Field(..., description="Total cache misses")
    total: int = Field(..., description="Total requests")


class AggregatedCacheMetrics(BaseModel):
    """Aggregated metrics across all cache types.

    Attributes:
        hit_rate: Combined cache hit rate (0.0-1.0)
        total_hits: Total hits across all caches
        total_requests: Total requests across all caches
    """

    hit_rate: float = Field(..., description="Combined cache hit rate (0.0-1.0)")
    total_hits: int = Field(..., description="Total hits across all caches")
    total_requests: int = Field(..., description="Total requests across all caches")


class UnifiedCacheMetricsResponse(BaseModel):
    """Response model for unified cache metrics across all cache systems.

    Aggregates metrics from:
    - Prompt cache: Anthropic native prompt caching
    - Research cache: PostgreSQL semantic similarity cache
    - LLM cache: Redis deterministic response cache

    Attributes:
        prompt: Anthropic prompt cache metrics (24h window)
        research: Research semantic cache metrics (24h window)
        llm: LLM response cache metrics (in-memory since startup)
        aggregate: Combined metrics across all caches
    """

    prompt: CacheTypeMetrics = Field(..., description="Anthropic prompt cache metrics")
    research: CacheTypeMetrics = Field(..., description="Research semantic cache metrics")
    llm: CacheTypeMetrics = Field(..., description="LLM response cache metrics")
    aggregate: AggregatedCacheMetrics = Field(..., description="Combined cache metrics")


# ==============================================================================
# Fair Usage Models
# ==============================================================================


class HeavyUserItem(BaseModel):
    """A user identified as heavy user for a feature.

    Attributes:
        user_id: User identifier
        email: User email (if available)
        feature: Feature name (mentor_chat, dataset_qa, etc.)
        total_cost_7d: Total cost over 7-day period
        avg_daily_cost: Average daily cost
        p90_threshold: p90 threshold for this feature
        exceeds_p90_by: How much they exceed p90
    """

    user_id: str = Field(..., description="User identifier")
    email: str | None = Field(None, description="User email")
    feature: str = Field(..., description="Feature name")
    total_cost_7d: float = Field(..., description="Total cost over 7 days (USD)")
    avg_daily_cost: float = Field(..., description="Average daily cost (USD)")
    p90_threshold: float = Field(..., description="p90 threshold for this feature (USD)")
    exceeds_p90_by: float = Field(..., description="Amount exceeding p90 (USD)")


class HeavyUsersResponse(BaseModel):
    """Response model for heavy users list.

    Attributes:
        heavy_users: List of heavy users
        total: Total count of heavy users
        period_days: Number of days in analysis period
    """

    heavy_users: list[HeavyUserItem] = Field(..., description="List of heavy users")
    total: int = Field(..., description="Total count")
    period_days: int = Field(..., description="Analysis period in days")


class FeatureCostBreakdown(BaseModel):
    """Cost breakdown for a single feature.

    Attributes:
        feature: Feature name
        total_cost: Total cost over period (USD)
        user_count: Number of unique users
        avg_per_user: Average cost per user (USD)
        p90_daily: p90 daily cost threshold (USD)
    """

    feature: str = Field(..., description="Feature name")
    total_cost: float = Field(..., description="Total cost over period (USD)")
    user_count: int = Field(..., description="Number of unique users")
    avg_per_user: float = Field(..., description="Average cost per user (USD)")
    p90_daily: float = Field(..., description="p90 daily cost threshold (USD)")


class FeatureCostBreakdownResponse(BaseModel):
    """Response model for feature cost breakdown.

    Attributes:
        features: List of feature breakdowns
        period_days: Number of days in analysis period
        total_cost: Total cost across all features
    """

    features: list[FeatureCostBreakdown] = Field(..., description="Feature breakdowns")
    period_days: int = Field(..., description="Analysis period in days")
    total_cost: float = Field(..., description="Total cost across all features (USD)")


# ==============================================================================
# Cost Aggregations Models
# ==============================================================================


class CategoryCostAggregation(BaseModel):
    """Cost aggregation for a single category.

    Attributes:
        category: Category name (llm, research, embeddings, etc.)
        total_cost: Total cost in USD
        avg_per_session: Average cost per session (None if no sessions)
        avg_per_user: Average cost per paying user (None if no paying users)
        session_count: Number of sessions in the period
        user_count: Number of paying users
    """

    category: str = Field(..., description="Category name")
    total_cost: float = Field(..., description="Total cost in USD")
    avg_per_session: float | None = Field(None, description="Average cost per session")
    avg_per_user: float | None = Field(None, description="Average cost per paying user")
    session_count: int = Field(..., description="Number of sessions in period")
    user_count: int = Field(..., description="Number of paying users")


class CostAggregationsResponse(BaseModel):
    """Response model for cost aggregations endpoint.

    Provides per-category cost breakdowns with per-meeting and per-user averages.

    Attributes:
        categories: List of per-category aggregations
        overall: Overall aggregation across all categories
        period_start: Start of the period (ISO 8601)
        period_end: End of the period (ISO 8601)
    """

    categories: list[CategoryCostAggregation] = Field(
        ..., description="Per-category cost aggregations"
    )
    overall: CategoryCostAggregation = Field(..., description="Overall aggregation")
    period_start: str = Field(..., description="Period start date (ISO 8601)")
    period_end: str = Field(..., description="Period end date (ISO 8601)")


# ==============================================================================
# Internal Costs Models
# ==============================================================================


class InternalCostItem(BaseModel):
    """Single internal cost entry.

    Attributes:
        provider: Provider name
        prompt_type: Type of prompt (blog_generation, blog_outline, etc.)
        total_cost: Total cost in USD
        request_count: Number of API calls
        input_tokens: Total input tokens
        output_tokens: Total output tokens
    """

    provider: str = Field(..., description="Provider name")
    prompt_type: str | None = Field(None, description="Prompt type")
    total_cost: float = Field(..., description="Total cost in USD")
    request_count: int = Field(..., description="Number of requests")
    input_tokens: int = Field(0, description="Total input tokens")
    output_tokens: int = Field(0, description="Total output tokens")


class InternalCostsByPeriod(BaseModel):
    """Internal costs aggregated by time period.

    Attributes:
        today: Costs from today
        week: Costs from last 7 days
        month: Costs from last 30 days
        all_time: All-time costs
    """

    today: float = Field(0.0, description="Cost today (USD)")
    week: float = Field(0.0, description="Cost this week (USD)")
    month: float = Field(0.0, description="Cost this month (USD)")
    all_time: float = Field(0.0, description="All-time cost (USD)")


class FeatureCostItem(BaseModel):
    """Single feature cost entry (user-facing features like mentor, dataset analysis).

    Attributes:
        feature: Feature name (mentor_chat, dataset_qa, etc.)
        provider: Provider name
        total_cost: Total cost in USD
        request_count: Number of API calls
        input_tokens: Total input tokens
        output_tokens: Total output tokens
        user_count: Number of unique users
    """

    feature: str = Field(..., description="Feature name")
    provider: str = Field(..., description="Provider name")
    total_cost: float = Field(..., description="Total cost in USD")
    request_count: int = Field(..., description="Number of requests")
    input_tokens: int = Field(0, description="Total input tokens")
    output_tokens: int = Field(0, description="Total output tokens")
    user_count: int = Field(0, description="Number of unique users")


class InternalCostsResponse(BaseModel):
    """Response model for internal costs endpoint.

    Attributes:
        seo: SEO-related internal costs breakdown
        system: System/background job costs breakdown
        data_analysis: Data analysis (dataset_qa) costs breakdown
        mentor_chat: Mentor chat costs breakdown
        by_period: Costs aggregated by time period
        total_usd: Total internal costs
        total_requests: Total number of API requests
    """

    seo: list[InternalCostItem] = Field(..., description="SEO costs breakdown")
    system: list[InternalCostItem] = Field(..., description="System costs breakdown")
    data_analysis: list[FeatureCostItem] = Field(
        default_factory=list, description="Data analysis costs breakdown"
    )
    mentor_chat: list[FeatureCostItem] = Field(
        default_factory=list, description="Mentor chat costs breakdown"
    )
    by_period: InternalCostsByPeriod = Field(..., description="Costs by period")
    total_usd: float = Field(..., description="Total internal costs (USD)")
    total_requests: int = Field(..., description="Total number of requests")


# ==============================================================================
# Cache/Model/Feature Insight Drill-Down Models
# ==============================================================================


class CacheEffectivenessBucket(BaseModel):
    """Cache effectiveness bucket for drill-down.

    Attributes:
        bucket_label: Human-readable bucket name (e.g., "0-25%", "25-50%")
        bucket_min: Minimum hit rate in bucket (0.0-1.0)
        bucket_max: Maximum hit rate in bucket (0.0-1.0)
        session_count: Number of sessions in this bucket
        avg_cost: Average cost per session (USD)
        total_cost: Total cost for sessions in bucket (USD)
        total_saved: Total cost saved via cache (USD)
        avg_optimization_savings: Average optimization savings per session (USD)
    """

    bucket_label: str = Field(..., description="Bucket label (e.g., '0-25%')")
    bucket_min: float = Field(..., description="Min hit rate in bucket")
    bucket_max: float = Field(..., description="Max hit rate in bucket")
    session_count: int = Field(..., description="Number of sessions in bucket")
    avg_cost: float = Field(..., description="Average cost per session (USD)")
    total_cost: float = Field(..., description="Total cost for bucket (USD)")
    total_saved: float = Field(..., description="Total cost saved (USD)")
    avg_optimization_savings: float = Field(..., description="Avg savings per session (USD)")


class CacheEffectivenessResponse(BaseModel):
    """Response model for cache effectiveness drill-down.

    Attributes:
        buckets: List of cache hit rate buckets with stats
        overall_hit_rate: Overall cache hit rate (0.0-1.0)
        total_sessions: Total sessions analyzed
        total_cost: Total cost across all sessions (USD)
        total_saved: Total cost saved across all sessions (USD)
        period: Time period filter applied
        min_sample_warning: Warning if sample size is low
    """

    buckets: list[CacheEffectivenessBucket] = Field(..., description="Hit rate buckets")
    overall_hit_rate: float = Field(..., description="Overall cache hit rate (0.0-1.0)")
    total_sessions: int = Field(..., description="Total sessions analyzed")
    total_cost: float = Field(..., description="Total cost (USD)")
    total_saved: float = Field(..., description="Total cost saved (USD)")
    period: str = Field(..., description="Time period filter applied")
    min_sample_warning: str | None = Field(None, description="Warning if sample size is low")


class ModelImpactItem(BaseModel):
    """Model impact stats for a single model.

    Attributes:
        model_name: Normalized model name
        model_display: Display-friendly model name
        request_count: Number of API requests
        total_cost: Total cost (USD)
        avg_cost_per_request: Average cost per request (USD)
        cache_hit_rate: Cache hit rate for this model (0.0-1.0)
        total_tokens: Total tokens used
    """

    model_name: str = Field(..., description="Normalized model name")
    model_display: str = Field(..., description="Display-friendly model name")
    request_count: int = Field(..., description="Number of API requests")
    total_cost: float = Field(..., description="Total cost (USD)")
    avg_cost_per_request: float = Field(..., description="Avg cost per request (USD)")
    cache_hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    total_tokens: int = Field(..., description="Total tokens used")


class ModelImpactResponse(BaseModel):
    """Response model for model impact drill-down.

    Attributes:
        models: List of per-model stats
        total_cost: Total cost across all models (USD)
        total_requests: Total API requests
        cost_if_all_opus: Hypothetical cost if all were Opus
        cost_if_all_haiku: Hypothetical cost if all were Haiku
        savings_from_model_mix: Actual savings from using model mix
        period: Time period filter applied
    """

    models: list[ModelImpactItem] = Field(..., description="Per-model stats")
    total_cost: float = Field(..., description="Total cost (USD)")
    total_requests: int = Field(..., description="Total API requests")
    cost_if_all_opus: float = Field(..., description="Hypothetical cost if all Opus (USD)")
    cost_if_all_haiku: float = Field(..., description="Hypothetical cost if all Haiku (USD)")
    savings_from_model_mix: float = Field(..., description="Savings from model mix (USD)")
    period: str = Field(..., description="Time period filter applied")


class FeatureEfficiencyItem(BaseModel):
    """Feature efficiency stats for a single feature.

    Attributes:
        feature: Feature name
        request_count: Number of API requests
        total_cost: Total cost (USD)
        avg_cost: Average cost per request (USD)
        cache_hit_rate: Cache hit rate for this feature (0.0-1.0)
        unique_sessions: Number of unique sessions using feature
        cost_per_session: Average cost per session using feature (USD)
    """

    feature: str = Field(..., description="Feature name")
    request_count: int = Field(..., description="Number of API requests")
    total_cost: float = Field(..., description="Total cost (USD)")
    avg_cost: float = Field(..., description="Avg cost per request (USD)")
    cache_hit_rate: float = Field(..., description="Cache hit rate (0.0-1.0)")
    unique_sessions: int = Field(..., description="Unique sessions using feature")
    cost_per_session: float = Field(..., description="Avg cost per session (USD)")


class FeatureEfficiencyResponse(BaseModel):
    """Response model for feature efficiency drill-down.

    Attributes:
        features: List of per-feature stats
        total_cost: Total cost across all features (USD)
        total_requests: Total API requests
        period: Time period filter applied
    """

    features: list[FeatureEfficiencyItem] = Field(..., description="Per-feature stats")
    total_cost: float = Field(..., description="Total cost (USD)")
    total_requests: int = Field(..., description="Total API requests")
    period: str = Field(..., description="Time period filter applied")


class TuningRecommendation(BaseModel):
    """Single tuning recommendation.

    Attributes:
        area: Area of recommendation (cache, model, feature)
        current_value: Current setting or metric value
        recommended_value: Recommended setting or target
        impact_description: Description of expected impact
        estimated_savings_usd: Estimated monthly savings (USD)
        confidence: Confidence level (low, medium, high)
    """

    area: str = Field(..., description="Area: cache, model, or feature")
    current_value: str = Field(..., description="Current setting or metric")
    recommended_value: str = Field(..., description="Recommended setting")
    impact_description: str = Field(..., description="Expected impact description")
    estimated_savings_usd: float | None = Field(None, description="Estimated monthly savings")
    confidence: str = Field(..., description="Confidence: low, medium, high")


class TuningRecommendationsResponse(BaseModel):
    """Response model for tuning recommendations endpoint.

    Attributes:
        recommendations: List of tuning recommendations
        analysis_period_days: Days of data analyzed
        data_quality: Quality of underlying data (sufficient, limited, insufficient)
    """

    recommendations: list[TuningRecommendation] = Field(..., description="Recommendations")
    analysis_period_days: int = Field(..., description="Days of data analyzed")
    data_quality: str = Field(..., description="Data quality: sufficient, limited, insufficient")


class QualityIndicatorsResponse(BaseModel):
    """Response model for quality correlation indicators.

    Attributes:
        overall_cache_hit_rate: Overall cache hit rate (0.0-1.0)
        session_continuation_rate: Rate of session continuation after response (0.0-1.0)
        correlation_score: Correlation between cache hit and continuation (-1.0 to 1.0)
        sample_size: Number of sessions in analysis
        cached_continuation_rate: Continuation rate for cached responses (0.0-1.0)
        uncached_continuation_rate: Continuation rate for uncached responses (0.0-1.0)
        quality_assessment: Human-readable quality assessment
        period: Time period filter applied
    """

    overall_cache_hit_rate: float = Field(..., description="Overall cache hit rate")
    session_continuation_rate: float = Field(..., description="Session continuation rate")
    correlation_score: float | None = Field(None, description="Cache-continuation correlation")
    sample_size: int = Field(..., description="Sessions analyzed")
    cached_continuation_rate: float | None = Field(None, description="Continuation for cached")
    uncached_continuation_rate: float | None = Field(None, description="Continuation for uncached")
    quality_assessment: str = Field(..., description="Human-readable assessment")
    period: str = Field(..., description="Time period filter applied")
