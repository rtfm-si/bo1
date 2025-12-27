# Emergency Access Procedures

This runbook documents emergency access procedures for Bo1 platform operations.

## 1. Admin Impersonation

### When to Use
- Investigating user-reported bugs that cannot be reproduced
- Debugging user-specific account issues
- Verifying user experience during support tickets
- Testing features as a specific user type

### Prerequisites
- Admin role in the system
- Documented reason for impersonation (required by audit)
- User consent where applicable (support tickets)

### Procedure

#### Start Impersonation (Read-Only)
```bash
# Via Admin Dashboard
1. Navigate to Admin → Users
2. Find target user
3. Click "Impersonate" button
4. Enter reason for impersonation
5. Select "Read-only" mode
6. Set duration (default 30 min, max 60 min)
```

```bash
# Via API (for automation/scripting)
curl -X POST "https://app.boardof.one/api/admin/impersonate/{user_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Bug investigation #12345",
    "write_mode": false,
    "duration_minutes": 30
  }'
```

#### Start Impersonation (Write Mode)
Use only when:
- User explicitly requests admin action on their behalf
- Critical data repair needed
- Migration or data cleanup required

```bash
curl -X POST "https://app.boardof.one/api/admin/impersonate/{user_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "User request: fix stuck meeting #54321",
    "write_mode": true,
    "duration_minutes": 15
  }'
```

#### Check Impersonation Status
```bash
curl "https://app.boardof.one/api/admin/impersonate/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### End Impersonation
```bash
# Via Dashboard: Click "End Impersonation" banner
# Via API:
curl -X DELETE "https://app.boardof.one/api/admin/impersonate" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Audit & Compliance
- All impersonation sessions are logged to `admin_impersonation_sessions` table
- ntfy alert is sent on impersonation start
- History available at `/api/admin/impersonate/history`

```bash
# View recent impersonation history
curl "https://app.boardof.one/api/admin/impersonate/history?limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Rollback
Impersonation automatically ends:
- After duration expires
- When admin explicitly ends session
- When admin logs out

No rollback needed - all actions during write-mode impersonation are attributed to target user.

---

## 2. Emergency Runtime Toggles

### When to Use
- Temporarily disable security features causing false positives
- Emergency disable of misbehaving features
- Quick feature toggles without server restart

### Available Toggles

| Key | Default | Purpose |
|-----|---------|---------|
| `prompt_injection_block_suspicious` | true | Block suspicious LLM prompts |
| `enable_llm_response_cache` | true | Cache LLM responses |
| `enable_prompt_cache` | true | Cache Anthropic prompt prefixes |
| `enable_sse_streaming` | true | Enable SSE event streaming |
| `auto_generate_projects` | true | Auto-generate project suggestions |
| `enable_context_collection` | true | Collect user context data |

### Procedure

#### List Current State
```bash
curl "https://app.boardof.one/api/admin/runtime-config" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Disable a Feature (Emergency)
```bash
# Example: Disable prompt injection blocking during false positive investigation
curl -X PATCH "https://app.boardof.one/api/admin/runtime-config/prompt_injection_block_suspicious" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": false}'
```

#### Re-enable Feature (Clear Override)
```bash
curl -X DELETE "https://app.boardof.one/api/admin/runtime-config/prompt_injection_block_suspicious" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Risks by Toggle

| Toggle | Risk When Disabled |
|--------|-------------------|
| `prompt_injection_block_suspicious` | **HIGH** - Allows potentially malicious prompts |
| `enable_llm_response_cache` | MEDIUM - Increased API costs, higher latency |
| `enable_prompt_cache` | MEDIUM - Increased API costs |
| `enable_sse_streaming` | LOW - Falls back to polling |
| `auto_generate_projects` | LOW - Projects not auto-created |
| `enable_context_collection` | MEDIUM - User context not collected |

### Audit
All toggle changes logged with:
- Admin user ID
- Key changed
- New value
- Timestamp

Check logs: `grep "ADMIN_RUNTIME_CONFIG" /var/log/bo1/api.log`

### Rollback
```bash
# Clear all overrides (revert to env defaults)
for key in prompt_injection_block_suspicious enable_llm_response_cache enable_prompt_cache enable_sse_streaming auto_generate_projects enable_context_collection; do
  curl -X DELETE "https://app.boardof.one/api/admin/runtime-config/$key" \
    -H "Authorization: Bearer $ADMIN_TOKEN"
done
```

---

## 3. Session Kill (Force-End Stuck Sessions)

### When to Use
- Meeting stuck in processing state
- SSE stream not completing
- Session consuming excessive resources

### Procedure

```bash
# Via Admin Dashboard
1. Navigate to Admin → Sessions
2. Find stuck session by ID or user
3. Click "Kill Session"
4. Confirm action

# Via API
curl -X DELETE "https://app.boardof.one/api/admin/sessions/{session_id}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### What Happens
- Session marked as `failed` with reason `admin_killed`
- Redis events cleared
- Client receives `session_killed` event
- User can start new session

### Rollback
Sessions cannot be un-killed. User must start new session.

---

## 4. Database Direct Access (Break-Glass)

### When to Use
- Critical data corruption
- Emergency migrations
- System recovery scenarios
- When API access is down

### Prerequisites
- SSH access to production server
- Database credentials (in vault)
- Incident ticket created

### Procedure

```bash
# 1. SSH to production
ssh root@139.59.201.65

# 2. Connect to database
docker exec -it boardofone-postgres-1 psql -U bo1 -d boardofone

# 3. Verify before making changes
SELECT * FROM users WHERE id = 'target-user-id';

# 4. Make minimal required changes
# ALWAYS use transactions
BEGIN;
UPDATE users SET status = 'active' WHERE id = 'target-user-id';
-- Verify
SELECT * FROM users WHERE id = 'target-user-id';
-- If correct:
COMMIT;
-- If wrong:
ROLLBACK;
```

### Audit Requirements
- Log all queries executed in incident ticket
- Screenshot or export of before/after state
- Notify team via Slack #incidents

### Rollback
```sql
-- Keep backup before any changes
CREATE TABLE backup_users_20251226 AS SELECT * FROM users WHERE id = 'target-user-id';

-- Rollback if needed
UPDATE users SET status = (SELECT status FROM backup_users_20251226 WHERE id = 'target-user-id')
WHERE id = 'target-user-id';
```

---

## 5. Emergency Contacts

| Role | Contact | Method |
|------|---------|--------|
| Primary On-Call | Si | ntfy / Slack |
| Database Admin | Si | ntfy / Slack |
| Infrastructure | Si | ntfy / Slack |

## 6. Related Documentation

- [Monitoring Runbook](./monitoring.md)
- [Alerting Runbook](./alerting.md)
- [GOVERNANCE.md](/GOVERNANCE.md) - <security> tag

---

_Last updated: 2025-12-26_
