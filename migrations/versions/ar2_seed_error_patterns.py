"""Seed common error patterns for AI ops self-healing.

Revision ID: ar2_seed_error_patterns
Revises: ar1_create_error_patterns
Create Date: 2025-12-13
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ar2_seed_error_patterns"
down_revision = "ar1_create_error_patterns"
branch_labels = None
depends_on = None


# Error patterns with their associated fixes
SEED_PATTERNS = [
    {
        "pattern_name": "redis_connection_refused",
        "pattern_regex": r"(Connection refused|ECONNREFUSED|Cannot connect to Redis|redis\.exceptions\.ConnectionError)",
        "error_type": "redis",
        "severity": "critical",
        "description": "Redis server unavailable or refusing connections",
        "threshold_count": 3,
        "threshold_window_minutes": 2,
        "cooldown_minutes": 5,
        "fixes": [
            {
                "fix_type": "reconnect_redis",
                "fix_config": {"max_retries": 3, "retry_delay_seconds": 2},
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "critical", "escalate": True},
                "priority": 2,
            },
        ],
    },
    {
        "pattern_name": "postgres_connection_pool_exhausted",
        "pattern_regex": r"(pool exhausted|connection pool|Too many connections|could not obtain a connection|QueuePool limit)",
        "error_type": "postgres",
        "severity": "high",
        "description": "Database connection pool saturated, requests waiting",
        "threshold_count": 5,
        "threshold_window_minutes": 3,
        "cooldown_minutes": 5,
        "fixes": [
            {
                "fix_type": "release_idle_connections",
                "fix_config": {"idle_timeout_seconds": 30},
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "high"},
                "priority": 2,
            },
        ],
    },
    {
        "pattern_name": "llm_rate_limit_exceeded",
        "pattern_regex": r"(rate_limit|429|too_many_requests|Rate limit reached|RateLimitError|APIConnectionError.*rate)",
        "error_type": "llm",
        "severity": "high",
        "description": "Anthropic/OpenAI rate limits exceeded",
        "threshold_count": 5,
        "threshold_window_minutes": 1,
        "cooldown_minutes": 2,
        "fixes": [
            {
                "fix_type": "circuit_break",
                "fix_config": {
                    "provider": "anthropic",
                    "fallback_provider": "openai",
                    "break_duration_seconds": 60,
                },
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "high"},
                "priority": 2,
            },
        ],
    },
    {
        "pattern_name": "sse_stream_timeout",
        "pattern_regex": r"(StreamTimeout|SSE.*timeout|ReadTimeout|stream.*timed out|connection.*closed.*unexpectedly)",
        "error_type": "sse",
        "severity": "medium",
        "description": "SSE streaming connection hung or timed out",
        "threshold_count": 3,
        "threshold_window_minutes": 5,
        "cooldown_minutes": 3,
        "fixes": [
            {
                "fix_type": "reset_sse_connections",
                "fix_config": {"max_age_seconds": 300},
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "medium"},
                "priority": 2,
            },
        ],
    },
    {
        "pattern_name": "memory_threshold_exceeded",
        "pattern_regex": r"(MemoryError|OutOfMemory|memory.*exceeded|Cannot allocate memory|killed.*OOM)",
        "error_type": "memory",
        "severity": "critical",
        "description": "Container memory pressure or OOM conditions",
        "threshold_count": 1,
        "threshold_window_minutes": 10,
        "cooldown_minutes": 10,
        "fixes": [
            {
                "fix_type": "clear_caches",
                "fix_config": {"caches": ["redis_local", "research_cache"]},
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "critical", "escalate": True},
                "priority": 2,
            },
        ],
    },
    {
        "pattern_name": "session_runaway",
        "pattern_regex": r"(runaway.*session|session.*exceeded|cost.*threshold|duration.*exceeded)",
        "error_type": "session",
        "severity": "high",
        "description": "Sessions exceeding time or cost limits",
        "threshold_count": 2,
        "threshold_window_minutes": 10,
        "cooldown_minutes": 5,
        "fixes": [
            {
                "fix_type": "kill_runaway_sessions",
                "fix_config": {
                    "max_duration_minutes": 60,
                    "max_cost_usd": 5.0,
                },
                "priority": 1,
            },
            {
                "fix_type": "alert_only",
                "fix_config": {"severity": "high"},
                "priority": 2,
            },
        ],
    },
]


def upgrade() -> None:
    """Seed initial error patterns and their fixes."""
    import json

    conn = op.get_bind()

    for pattern_data in SEED_PATTERNS:
        # Insert pattern
        fixes = pattern_data.pop("fixes")
        result = conn.execute(
            sa.text("""
            INSERT INTO error_patterns (
                pattern_name, pattern_regex, error_type, severity,
                description, threshold_count, threshold_window_minutes, cooldown_minutes
            ) VALUES (
                :pattern_name, :pattern_regex, :error_type, :severity,
                :description, :threshold_count, :threshold_window_minutes, :cooldown_minutes
            )
            ON CONFLICT (pattern_name) DO UPDATE SET
                pattern_regex = EXCLUDED.pattern_regex,
                error_type = EXCLUDED.error_type,
                severity = EXCLUDED.severity,
                description = EXCLUDED.description,
                threshold_count = EXCLUDED.threshold_count,
                threshold_window_minutes = EXCLUDED.threshold_window_minutes,
                cooldown_minutes = EXCLUDED.cooldown_minutes,
                updated_at = now()
            RETURNING id
            """),
            pattern_data,
        )
        pattern_id = result.fetchone()[0]

        # Insert fixes for this pattern
        for fix in fixes:
            conn.execute(
                sa.text("""
                INSERT INTO error_fixes (error_pattern_id, fix_type, fix_config, priority)
                VALUES (:pattern_id, :fix_type, :fix_config, :priority)
                ON CONFLICT DO NOTHING
                """),
                {
                    "pattern_id": pattern_id,
                    "fix_type": fix["fix_type"],
                    "fix_config": json.dumps(fix["fix_config"]),
                    "priority": fix["priority"],
                },
            )


def downgrade() -> None:
    """Remove seeded error patterns."""
    conn = op.get_bind()
    pattern_names = [p["pattern_name"] for p in SEED_PATTERNS]
    placeholders = ", ".join([f"'{name}'" for name in pattern_names])
    conn.execute(sa.text(f"DELETE FROM error_patterns WHERE pattern_name IN ({placeholders})"))
