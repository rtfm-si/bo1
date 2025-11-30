-- Data Persistence Verification Query
-- Purpose: Ensure that deliberations are saving data correctly
-- Run frequency: Hourly or after each deployment
-- Alert: If sessions exist but no contributions saved = CRITICAL

-- Check that recent sessions have data persisted
WITH recent_sessions AS (
    SELECT id, created_at, status FROM sessions
    WHERE created_at > NOW() - INTERVAL '24 hours'
)
SELECT
    COUNT(DISTINCT s.id) as sessions_created_24h,
    COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) as completed_sessions,
    COUNT(DISTINCT c.session_id) as sessions_with_contributions,
    COUNT(c.id) as total_contributions,
    COUNT(DISTINCT ac.session_id) as sessions_with_api_costs,
    COUNT(ac.id) as total_api_cost_records,
    COUNT(DISTINCT se.session_id) as sessions_with_events,
    COUNT(se.id) as total_events,
    CASE
        WHEN COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) > 0
         AND COUNT(DISTINCT c.session_id) = 0
        THEN '🚨 CRITICAL: Completed sessions but NO contributions saved!'
        WHEN COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END) > 0
         AND COUNT(DISTINCT ac.session_id) = 0
        THEN '🚨 CRITICAL: Completed sessions but NO API costs tracked!'
        WHEN COUNT(DISTINCT s.id) = 0
        THEN 'ℹ️ INFO: No sessions in last 24h (expected if no traffic).'
        WHEN COUNT(DISTINCT c.session_id)::float / NULLIF(COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.id END), 0) < 0.8
        THEN '⚠️ WARNING: Less than 80% of completed sessions have contributions.'
        ELSE '✅ OK: Data persistence working correctly.'
    END as status
FROM recent_sessions s
LEFT JOIN contributions c ON s.id = c.session_id
LEFT JOIN api_costs ac ON s.id = ac.session_id
LEFT JOIN session_events se ON s.id = se.session_id;

-- Per-session data integrity check
SELECT
    s.id as session_id,
    s.status,
    s.created_at,
    s.completed_at,
    COUNT(DISTINCT c.id) as contribution_count,
    COUNT(DISTINCT ac.id) as api_cost_count,
    COUNT(DISTINCT se.id) as event_count,
    CASE
        WHEN s.status = 'completed' AND COUNT(DISTINCT c.id) = 0 THEN '🚨 NO CONTRIBUTIONS'
        WHEN s.status = 'completed' AND COUNT(DISTINCT ac.id) = 0 THEN '⚠️ NO COSTS TRACKED'
        WHEN s.status = 'completed' THEN '✅ OK'
        WHEN s.status IN ('active', 'paused') THEN '⏳ IN PROGRESS'
        ELSE '❌ FAILED'
    END as data_status
FROM sessions s
LEFT JOIN contributions c ON s.id = c.session_id
LEFT JOIN api_costs ac ON s.id = ac.session_id
LEFT JOIN session_events se ON s.id = se.session_id
WHERE s.created_at > NOW() - INTERVAL '24 hours'
GROUP BY s.id, s.status, s.created_at, s.completed_at
ORDER BY s.created_at DESC
LIMIT 20;

-- User_id backfill verification
SELECT
    'contributions' as table_name,
    COUNT(*) as total_rows,
    COUNT(user_id) as rows_with_user_id,
    COUNT(*) - COUNT(user_id) as rows_missing_user_id,
    CASE
        WHEN COUNT(*) - COUNT(user_id) > 0 THEN '⚠️ WARNING: NULL user_id rows found!'
        ELSE '✅ OK'
    END as status
FROM contributions
UNION ALL
SELECT
    'api_costs',
    COUNT(*),
    COUNT(user_id),
    COUNT(*) - COUNT(user_id),
    CASE
        WHEN COUNT(*) - COUNT(user_id) > 0 THEN '⚠️ WARNING: NULL user_id rows found!'
        ELSE '✅ OK'
    END
FROM api_costs
UNION ALL
SELECT
    'session_events',
    COUNT(*),
    COUNT(user_id),
    COUNT(*) - COUNT(user_id),
    CASE
        WHEN COUNT(*) - COUNT(user_id) > 0 THEN '⚠️ WARNING: NULL user_id rows found!'
        ELSE '✅ OK'
    END
FROM session_events;
