-- Query Performance Monitoring
-- Purpose: Identify slow queries and unused indexes
-- Requirements: pg_stat_statements extension enabled
-- Run frequency: Weekly or when performance degrades

-- Enable pg_stat_statements if not already enabled
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 20 slowest queries (by mean execution time)
SELECT
    LEFT(query, 100) as query_preview,
    calls,
    ROUND(total_exec_time::numeric, 2) as total_time_ms,
    ROUND(mean_exec_time::numeric, 2) as mean_time_ms,
    ROUND(max_exec_time::numeric, 2) as max_time_ms,
    ROUND(stddev_exec_time::numeric, 2) as stddev_ms,
    CASE
        WHEN mean_exec_time > 1000 THEN '🚨 CRITICAL: >1s avg'
        WHEN mean_exec_time > 500 THEN '⚠️ WARNING: >500ms avg'
        WHEN mean_exec_time > 100 THEN 'ℹ️ INFO: >100ms avg'
        ELSE '✅ OK'
    END as status
FROM pg_stat_statements
WHERE query LIKE '%contributions%'
   OR query LIKE '%api_costs%'
   OR query LIKE '%session_events%'
   OR query LIKE '%sessions%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    CASE
        WHEN idx_scan = 0 AND pg_relation_size(indexrelid) > 1048576 THEN '🚨 CRITICAL: Unused index >1MB!'
        WHEN idx_scan = 0 THEN '⚠️ WARNING: Index never used'
        WHEN idx_scan < 10 THEN 'ℹ️ INFO: Index rarely used'
        ELSE '✅ OK'
    END as status
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND tablename IN ('contributions', 'api_costs', 'session_events', 'session_tasks', 'sessions')
ORDER BY
    CASE
        WHEN idx_scan = 0 THEN 0
        ELSE 1
    END,
    idx_scan ASC,
    pg_relation_size(indexrelid) DESC;

-- Table scan vs index scan ratio
SELECT
    schemaname,
    relname as tablename,
    seq_scan as sequential_scans,
    idx_scan as index_scans,
    ROUND(100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0), 2) as index_scan_pct,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    CASE
        WHEN (seq_scan + idx_scan) > 100 AND
             (100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0)) < 50
        THEN '⚠️ WARNING: Low index usage (<50%)'
        WHEN (seq_scan + idx_scan) > 100 AND
             (100.0 * idx_scan / NULLIF(seq_scan + idx_scan, 0)) < 80
        THEN 'ℹ️ INFO: Consider more indexes'
        ELSE '✅ OK'
    END as status
FROM pg_stat_user_tables
WHERE schemaname = 'public'
AND relname IN ('contributions', 'api_costs', 'session_events', 'session_tasks', 'sessions')
ORDER BY seq_scan DESC;

-- Cache hit ratio (should be >90%)
SELECT
    'Buffer cache hit ratio' as metric,
    ROUND(
        100.0 * sum(blks_hit) / NULLIF(sum(blks_hit + blks_read), 0),
        2
    ) as hit_ratio_pct,
    CASE
        WHEN ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit + blks_read), 0), 2) < 90
        THEN '⚠️ WARNING: Cache hit ratio <90%'
        WHEN ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit + blks_read), 0), 2) < 95
        THEN 'ℹ️ INFO: Consider increasing shared_buffers'
        ELSE '✅ OK: Good cache performance'
    END as status
FROM pg_stat_database
WHERE datname = current_database();

-- Bloat estimation (tables that may need VACUUM)
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    n_dead_tup as dead_tuples,
    n_live_tup as live_tuples,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 2) as bloat_pct,
    last_vacuum,
    last_autovacuum,
    CASE
        WHEN n_dead_tup > 10000 AND
             (100.0 * n_dead_tup / NULLIF(n_live_tup, 0)) > 20
        THEN '🚨 CRITICAL: Run VACUUM! >20% bloat'
        WHEN n_dead_tup > 5000 AND
             (100.0 * n_dead_tup / NULLIF(n_live_tup, 0)) > 10
        THEN '⚠️ WARNING: Consider VACUUM (>10% bloat)'
        ELSE '✅ OK'
    END as status
FROM pg_stat_user_tables
WHERE schemaname = 'public'
AND tablename IN ('contributions', 'api_costs', 'session_events', 'session_tasks', 'sessions')
ORDER BY n_dead_tup DESC;
