# PostgreSQL Session Persistence - Quick Start

## What Was Fixed

Sessions now persist to PostgreSQL (permanent) in addition to Redis (24-hour cache), ensuring meeting history survives container restarts and TTL expiry.

## Apply Migration

```bash
# Start services
make up

# Apply migration (creates/updates sessions table)
make shell
psql $DATABASE_URL -f bo1/database/migrations/009_ensure_sessions_table.sql
exit
```

## Verify It Works

```bash
# Run verification script
make shell
python scripts/verify_session_persistence.py
exit

# Expected: All tests pass ✅
```

## Test Flow

1. **Create a session** via API → Saved to both Redis AND PostgreSQL
2. **Start deliberation** → Status updated to 'running' in PostgreSQL
3. **Complete deliberation** → Status updated to 'completed' with synthesis in PostgreSQL
4. **Restart containers** (`make down && make up`) → Sessions still appear in dashboard
5. **Wait 24+ hours** (or manually delete Redis keys) → Sessions still appear in dashboard

## Key Behavior Changes

| Action | Before | After |
|--------|--------|-------|
| Create session | Redis only (24h TTL) | Redis + PostgreSQL (permanent) |
| List sessions | Redis query only | PostgreSQL query + Redis enrichment |
| After restart | Sessions disappear | Sessions persist from PostgreSQL |
| After 24 hours | Sessions disappear | Sessions persist from PostgreSQL |
| Session status updates | Redis only | Redis + PostgreSQL |

## Files Changed

- `bo1/database/migrations/009_ensure_sessions_table.sql` - New migration
- `bo1/state/postgres_manager.py` - 4 new functions (save_session, update_session_status, get_session, get_user_sessions)
- `backend/api/sessions.py` - Create/list sessions now use PostgreSQL
- `backend/api/event_collector.py` - Completion/error handlers update PostgreSQL status
- `backend/api/control.py` - Start/kill handlers update PostgreSQL status

## Monitoring

Watch logs for:
- ✅ `"Created session: {id} for user: {user_id} (saved to both Redis and PostgreSQL)"`
- ✅ `"Loaded {N} sessions from PostgreSQL for user {user_id}"`
- ✅ `"Updated session {id} status to 'completed' in PostgreSQL"`
- ⚠️  `"Failed to save to PostgreSQL (Redis saved successfully)"` - Non-fatal, session continues

## Rollback Plan

If issues arise:
1. PostgreSQL failures are non-fatal - sessions continue with Redis only
2. Revert code changes to restore Redis-only behavior
3. Migration is idempotent - safe to re-run if needed

## Next Steps

After verifying:
1. Test creating a new session
2. Verify it appears in PostgreSQL: `SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5;`
3. Restart containers and verify dashboard still shows sessions
4. Monitor logs for any PostgreSQL errors
