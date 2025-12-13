# Plan: AI Ops Self-Healing [OPS][P3]

## Summary

- Implement error pattern detection service analyzing logs and metrics
- Create known-error to known-fix mapping database
- Build automated recovery procedures for common failure modes
- Create self-monitoring dashboard with health status and auto-remediation history

## Implementation Steps

- Step 1: Create error patterns migration
  - `migrations/versions/ar1_create_error_patterns.py`
  - Tables:
    - `error_patterns` (id, pattern_name, pattern_regex, error_type, severity, description, created_at)
    - `error_fixes` (id, error_pattern_id FK, fix_type enum, fix_config JSONB, success_rate, last_applied_at)
    - `auto_remediation_log` (id, error_pattern_id FK, error_fix_id FK, triggered_at, outcome enum, details JSONB)

- Step 2: Seed common error patterns
  - `migrations/versions/ar2_seed_error_patterns.py`
  - Patterns:
    - `redis_connection_refused` - Redis unavailable
    - `postgres_connection_pool_exhausted` - DB pool saturation
    - `llm_rate_limit_exceeded` - Anthropic/OpenAI rate limits
    - `sse_stream_timeout` - Streaming connection hung
    - `memory_threshold_exceeded` - Container memory pressure
    - `session_runaway` - Sessions exceeding time/cost limits

- Step 3: Create error pattern detection service
  - `backend/services/error_detector.py`:
    - `detect_patterns(log_entries: list[str]) -> list[DetectedError]`
    - `match_error_to_pattern(error_msg: str) -> ErrorPattern | None`
    - `get_error_frequency(pattern_id, window_minutes=60) -> int`
    - `should_trigger_remediation(pattern_id) -> bool` (frequency thresholds)

- Step 4: Create automated recovery service
  - `backend/services/auto_remediation.py`:
    - `RemediationType` enum: restart_service, clear_cache, scale_connection_pool, circuit_break, alert_only
    - `get_fix_for_pattern(pattern_id) -> ErrorFix | None`
    - `execute_fix(error_fix: ErrorFix, context: dict) -> RemediationResult`
    - `log_remediation(pattern_id, fix_id, outcome, details)`
    - Fix implementations:
      - `_fix_redis_reconnect()` - flush bad connections, reconnect
      - `_fix_db_pool_reset()` - release idle connections
      - `_fix_llm_circuit_break()` - temporary fallback to secondary provider
      - `_fix_session_kill()` - terminate runaway sessions

- Step 5: Create background monitoring job
  - `backend/jobs/error_monitor.py`:
    - Runs every 30 seconds
    - Fetches recent error logs from Loki/Redis
    - Calls `detect_patterns()` + `should_trigger_remediation()`
    - Executes fixes when thresholds exceeded
    - Sends ntfy alert on remediation action

- Step 6: Add admin API endpoints
  - `backend/api/admin/ops.py`:
    - `GET /api/admin/ops/patterns` - list error patterns with stats
    - `GET /api/admin/ops/remediations` - recent auto-remediation log
    - `POST /api/admin/ops/patterns` - add custom pattern
    - `PATCH /api/admin/ops/patterns/{id}` - update pattern/fix config
    - `GET /api/admin/ops/health` - system health overview

- Step 7: Create self-monitoring dashboard
  - `frontend/src/routes/(app)/admin/ops/+page.svelte`:
    - System health overview (Redis, Postgres, LLM providers)
    - Error pattern frequency chart (last 24h)
    - Auto-remediation history table
    - Pattern management UI (view/edit patterns)
    - Manual remediation triggers (emergency buttons)

## Tests

- Unit tests:
  - `tests/services/test_error_detector.py`:
    - `test_pattern_matching()` - regex matches expected errors
    - `test_frequency_threshold()` - triggers at correct count
    - `test_no_match_unknown_error()` - graceful handling
  - `tests/services/test_auto_remediation.py`:
    - `test_execute_fix_success()` - fix runs and logs
    - `test_fix_failure_logged()` - failures recorded
    - `test_circuit_breaker_applied()` - LLM fallback works

- Integration tests:
  - `tests/api/test_ops_admin.py`:
    - `test_patterns_endpoint()` - lists patterns
    - `test_remediations_endpoint()` - shows history
    - `test_health_endpoint()` - returns status

- Manual validation:
  - Simulate Redis disconnect, verify auto-reconnect
  - Trigger rate limit, verify circuit breaker engages
  - Check dashboard shows remediation event

## Dependencies & Risks

- Dependencies:
  - Existing monitoring (vendor_health.py, service_monitor.py)
  - Existing alerting (alerts.py, ntfy integration)
  - Existing session monitoring (session_monitoring.py)
  - Loki logs or Redis error buffer for pattern detection

- Risks/edge cases:
  - Remediation loops: fix triggers same error
    - Mitigation: cooldown period (5min) after remediation
  - False positives: pattern too broad
    - Mitigation: require N occurrences in window before action
  - Fix makes things worse:
    - Mitigation: alert_only mode for new patterns, success_rate tracking
  - Multiple patterns match same error:
    - Mitigation: severity ranking, apply highest priority fix only
