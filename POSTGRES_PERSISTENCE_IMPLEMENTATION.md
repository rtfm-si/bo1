# PostgreSQL Session Persistence Implementation

## Overview

Fixed critical data persistence issue where meetings/sessions were only saved to Redis (24-hour TTL) and disappeared from the dashboard after TTL expiry or container restarts. Sessions are now persisted to PostgreSQL as the primary source of truth, with Redis serving as a cache for live session state.

## Problem Statement

**Before:**
- Sessions created via `POST /api/v1/sessions` were only saved to Redis
- Redis has 24-hour TTL on all session data
- Dashboard queried Redis only via `list_sessions()` endpoint
- After TTL expiry or container restart, all meeting history was lost
- PostgreSQL `sessions` table existed but was never used

**After:**
- Sessions are saved to BOTH Redis (live cache) AND PostgreSQL (permanent record)
- Dashboard queries PostgreSQL first for persistent data
- Redis enriches with live state for active sessions (status, cost, last_activity)
- Meeting history persists across restarts and beyond 24-hour TTL
- Session status updates (running, completed, failed, killed) are persisted to PostgreSQL

## Architecture

```
Session Lifecycle → Dual Storage Strategy:
├── Redis: Live state cache (24h TTL)
│   ├── Fast access for active sessions
│   ├── Real-time metadata (last_activity_at, live cost)
│   └── Automatic cleanup after 24 hours
│
└── PostgreSQL: Permanent record (infinite retention)
    ├── Primary source of truth
    ├── Historical session data
    ├── Status tracking (created → running → completed/failed/killed)
    └── Synthesis and final results
```

## Files Modified

### 1. Migration: `bo1/database/migrations/009_ensure_sessions_table.sql`
- Creates `sessions` table if it doesn't exist
- Adds indexes on `user_id`, `created_at`, `status`
- Ensures columns `synthesis_text` and `final_recommendation` exist
- Converts `problem_context` from JSON to JSONB for better querying

**Key Fields:**
- `id` (VARCHAR): Session identifier (e.g., `bo1_uuid`)
- `user_id` (VARCHAR): User who created the session
- `problem_statement` (TEXT): Original problem
- `problem_context` (JSONB): Additional context
- `status` (VARCHAR): created | running | completed | failed | killed | deleted
- `phase` (VARCHAR): Current deliberation phase
- `total_cost` (NUMERIC): Total cost in USD
- `round_number` (INTEGER): Current round
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE)
- `synthesis_text` (TEXT): Final synthesis XML
- `final_recommendation` (TEXT): Final recommendation

### 2. Database Functions: `bo1/state/postgres_manager.py`

Added 4 new functions:

#### `save_session(session_id, user_id, problem_statement, problem_context, status='created')`
- **Purpose**: Insert new session to PostgreSQL
- **Strategy**: `ON CONFLICT DO UPDATE` (upsert pattern)
- **Returns**: Saved session record with timestamps

#### `update_session_status(session_id, status, **kwargs)`
- **Purpose**: Update session status and optional fields
- **Dynamic**: Only updates provided fields (phase, total_cost, round_number, synthesis_text, final_recommendation)
- **Returns**: True if updated successfully

#### `get_session(session_id)`
- **Purpose**: Retrieve single session by ID
- **Returns**: Session dict or None if not found

#### `get_user_sessions(user_id, limit=50, offset=0, status_filter=None)`
- **Purpose**: List all sessions for a user with pagination
- **Ordering**: `created_at DESC` (most recent first)
- **Filtering**: Optional status filter (e.g., 'completed', 'running')
- **Returns**: List of session records

### 3. Session Creation: `backend/api/sessions.py`

**Updated `create_session()` endpoint (lines 120-132):**
```python
# Save metadata to Redis (for live state and fast lookup)
redis_manager.save_metadata(session_id, metadata)
redis_manager.add_session_to_user_index(user_id, session_id)

# Save session to PostgreSQL for permanent storage
try:
    save_session(
        session_id=session_id,
        user_id=user_id,
        problem_statement=request.problem_statement,
        problem_context=request.problem_context,
        status="created",
    )
    logger.info("Created session (saved to both Redis and PostgreSQL)")
except Exception as e:
    logger.error("Failed to save to PostgreSQL (Redis saved successfully)")
    # Don't fail request - Redis is sufficient for session to continue
```

**Strategy:** Save to both sources, but don't fail if PostgreSQL fails (Redis is sufficient).

### 4. Session Listing: `backend/api/sessions.py`

**Updated `list_sessions()` endpoint (lines 184-349):**

**Primary Source: PostgreSQL**
1. Query `get_user_sessions(user_id, limit, offset, status_filter)`
2. If Postgres returns sessions, enrich with Redis live metadata
3. For each session, check if Redis has newer data (for active sessions)
4. Use Redis data if `updated_at` is more recent (e.g., live cost updates)
5. Return enriched session list

**Fallback: Redis**
- If PostgreSQL fails or returns empty, fall back to Redis-only query
- Uses existing `list_user_sessions()` and `batch_load_metadata()` logic
- Maintains backward compatibility

**Example Flow:**
```
User requests dashboard
  → Query PostgreSQL: get_user_sessions(user_id)
  → For each session:
      → Load Redis metadata (if available)
      → Compare updated_at timestamps
      → Use Redis data if newer (live session)
      → Use Postgres data if older (historical session)
  → Return unified session list
```

### 5. Session Status Updates: `backend/api/event_collector.py`

**Updated `_handle_completion()` method (lines 537-557):**
- Extracts final data: synthesis_text, total_cost, round_number, phase
- Calls `update_session_status()` with status='completed'
- Logs success or error (doesn't fail completion event)

**Updated `collect_and_publish()` exception handler (lines 220-226):**
- On graph execution error, updates status to 'failed'
- Ensures failed sessions are persisted with error state

### 6. Control Endpoints: `backend/api/control.py`

**Updated `start_deliberation()` endpoint (lines 187-193):**
- After starting background task, updates status to 'running'
- Logs success or error (doesn't fail start request)

**Updated `kill_deliberation()` endpoint (lines 432-438):**
- After killing session, updates status to 'killed'
- Logs success or error (doesn't fail kill request)

## Testing

### Run Migration
```bash
# Start database
make up

# Apply migration
psql $DATABASE_URL -f bo1/database/migrations/009_ensure_sessions_table.sql
```

### Verify Implementation
```bash
# Run verification script
python scripts/verify_session_persistence.py
```

**Expected Output:**
```
[TEST 1] Saving new session to PostgreSQL...
✅ Session saved: bo1_test_1234567890.123

[TEST 2] Retrieving session from PostgreSQL...
✅ Session retrieved: bo1_test_1234567890.123

[TEST 3] Updating session status...
✅ Session status updated
   New status: running
   Phase: decomposition
   Round: 1

[TEST 4] Listing user sessions...
✅ Found 1 sessions for user test_user_123

[TEST 5] Updating session to completed with synthesis...
✅ Session marked as completed
   Status: completed
   Total cost: $0.42

[TEST 6] Filtering sessions by status...
✅ Found 1 completed sessions

✅ All tests passed! Session persistence is working correctly.
```

### Manual Testing

**Test 1: Create Session**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"problem_statement": "Test problem", "problem_context": {}}'
```

**Test 2: Verify in PostgreSQL**
```sql
SELECT id, user_id, status, created_at
FROM sessions
ORDER BY created_at DESC
LIMIT 5;
```

**Test 3: Verify Persistence After Restart**
```bash
# Restart containers
make down && make up

# List sessions via API
curl http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN"

# Sessions should still appear (from PostgreSQL)
```

**Test 4: Verify 24h+ Persistence**
```bash
# Manually expire Redis keys
redis-cli KEYS "session:*" | xargs redis-cli DEL
redis-cli KEYS "metadata:*" | xargs redis-cli DEL

# List sessions via API
curl http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN"

# Sessions should still appear (from PostgreSQL)
```

## Error Handling Strategy

All PostgreSQL operations follow this pattern:
```python
try:
    # Attempt PostgreSQL operation
    save_session(session_id, user_id, ...)
    logger.info("Success message")
except Exception as e:
    logger.error(f"Failed to save to PostgreSQL: {e}")
    # DON'T FAIL REQUEST - Redis is sufficient
```

**Rationale:**
- Redis is sufficient for active sessions to continue
- PostgreSQL failures shouldn't break user workflows
- Errors are logged for debugging and monitoring
- Graceful degradation maintains system availability

## Benefits

1. **Data Persistence**: Sessions survive container restarts and Redis TTL expiry
2. **Historical Record**: Complete audit trail of all deliberations
3. **Performance**: Redis still provides fast access for active sessions
4. **Scalability**: PostgreSQL handles long-term storage and complex queries
5. **Reliability**: Dual storage provides redundancy and fallback options
6. **User Experience**: Dashboard always shows full session history

## Backward Compatibility

- Existing Redis-only sessions continue to work
- Redis fallback ensures no disruption during migration
- Migration is idempotent (safe to run multiple times)
- No breaking changes to API contracts

## Future Improvements

1. **Periodic Sync**: Background job to sync Redis → PostgreSQL for active sessions
2. **Metrics**: Track PostgreSQL vs Redis hit rates for session listing
3. **Caching Strategy**: Implement read-through cache for frequently accessed sessions
4. **Archival**: Move old completed sessions to archive table
5. **Analytics**: Build dashboard metrics from PostgreSQL session data

## Monitoring

Watch for these log messages:

**Success:**
- `"Created session: {session_id} for user: {user_id} (saved to both Redis and PostgreSQL)"`
- `"Loaded {N} sessions from PostgreSQL for user {user_id}"`
- `"Updated session {session_id} status to 'completed' in PostgreSQL"`

**Warnings:**
- `"Failed to save session to PostgreSQL (Redis saved successfully)"`
- `"Failed to load sessions from PostgreSQL: {error}, falling back to Redis"`
- `"Failed to update session status in PostgreSQL: {error}"`

## Summary

This implementation establishes PostgreSQL as the primary source of truth for session data while maintaining Redis as a performance cache for active sessions. The dual-storage strategy ensures data persistence beyond Redis TTL while preserving fast access patterns for live sessions. All status transitions (created → running → completed/failed/killed) are now permanently recorded in PostgreSQL, providing a complete audit trail for all deliberations.
