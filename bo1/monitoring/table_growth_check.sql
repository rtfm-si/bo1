-- Table Growth Monitoring Query
-- Purpose: Monitor table sizes and row counts to detect when partitioning is needed
-- Run frequency: Daily via cron or GitHub Actions
-- Alert thresholds: 100K rows = INFO, 250K = WARNING, 500K = CRITICAL

-- Table size and row count estimates
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size,
    pg_total_relation_size(schemaname||'.'||tablename) AS bytes,
    (SELECT reltuples::bigint FROM pg_class WHERE relname = t.tablename) AS estimated_rows
FROM pg_tables t
WHERE schemaname = 'public'
AND tablename IN ('api_costs', 'session_events', 'contributions', 'session_tasks', 'sessions', 'users')
ORDER BY bytes DESC;

-- Alert thresholds with status
SELECT
    tablename,
    row_count,
    pg_size_pretty(size_bytes) as size,
    CASE
        WHEN row_count > 500000 THEN 'CRITICAL: Partition now! Approaching 1M row limit.'
        WHEN row_count > 250000 THEN 'WARNING: Consider partitioning soon (50%+ to threshold).'
        WHEN row_count > 100000 THEN 'INFO: Monitor growth rate closely.'
        ELSE 'OK'
    END as status,
    CASE
        WHEN row_count > 500000 THEN '🚨'
        WHEN row_count > 250000 THEN '⚠️'
        WHEN row_count > 100000 THEN 'ℹ️'
        ELSE '✅'
    END as indicator
FROM (
    SELECT 'api_costs' as tablename, COUNT(*) as row_count, pg_total_relation_size('api_costs') as size_bytes FROM api_costs
    UNION ALL
    SELECT 'session_events', COUNT(*), pg_total_relation_size('session_events') FROM session_events
    UNION ALL
    SELECT 'contributions', COUNT(*), pg_total_relation_size('contributions') FROM contributions
    UNION ALL
    SELECT 'session_tasks', COUNT(*), pg_total_relation_size('session_tasks') FROM session_tasks
    UNION ALL
    SELECT 'sessions', COUNT(*), pg_total_relation_size('sessions') FROM sessions
) t
ORDER BY row_count DESC;

-- Growth rate analysis (7-day trend)
SELECT
    tablename,
    rows_today,
    rows_7days_ago,
    rows_today - rows_7days_ago as growth_7days,
    ROUND((rows_today - rows_7days_ago)::numeric / NULLIF(rows_7days_ago, 0) * 100, 2) as growth_pct,
    CASE
        WHEN rows_7days_ago > 0 THEN
            ROUND((500000 - rows_today)::numeric / NULLIF((rows_today - rows_7days_ago)::numeric / 7, 0), 0)
        ELSE NULL
    END as days_until_500k
FROM (
    SELECT
        'api_costs' as tablename,
        (SELECT COUNT(*) FROM api_costs) as rows_today,
        (SELECT COUNT(*) FROM api_costs WHERE created_at < NOW() - INTERVAL '7 days') as rows_7days_ago
    UNION ALL
    SELECT
        'session_events',
        (SELECT COUNT(*) FROM session_events),
        (SELECT COUNT(*) FROM session_events WHERE created_at < NOW() - INTERVAL '7 days')
    UNION ALL
    SELECT
        'contributions',
        (SELECT COUNT(*) FROM contributions),
        (SELECT COUNT(*) FROM contributions WHERE created_at < NOW() - INTERVAL '7 days')
) t;
