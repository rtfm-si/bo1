# Database Migrations

This directory contains Alembic database migrations for Board of One.

## Running Migrations

### Apply all pending migrations:
```bash
uv run alembic upgrade head
```

### Rollback one migration:
```bash
uv run alembic downgrade -1
```

### View migration history:
```bash
uv run alembic history
```

### Check current version:
```bash
uv run alembic current
```

## Creating New Migrations

### Auto-generate migration from model changes:
```bash
uv run alembic revision --autogenerate -m "description"
```

### Create empty migration:
```bash
uv run alembic revision -m "description"
```

**Important:** Always review auto-generated migrations before applying!

## Migration Structure

Each migration has:
- `upgrade()` - Apply the migration
- `downgrade()` - Rollback the migration

## Testing Migrations

Before committing a new migration:

1. Apply migration: `uv run alembic upgrade head`
2. Test application with new schema
3. Rollback: `uv run alembic downgrade -1`
4. Re-apply: `uv run alembic upgrade head`
5. Verify idempotency (can run multiple times safely)

## Database Indexes

### Current Performance Indexes

**user_context table:**
- `idx_user_context_user_id` - Fast user lookups

**session_clarifications table:**
- `idx_clarifications_session` - Fast session lookups

**research_cache table:**
- `idx_research_cache_category` - Fast category filtering
- `idx_research_cache_industry` - Fast industry filtering
- `idx_research_cache_research_date` - Fast date-based queries (DESC order)

**sessions table:**
- `idx_sessions_user_id` - Fast user session lookups
- `idx_sessions_status` - Fast status filtering
- `idx_sessions_created_at` - Fast date sorting

**actions table:**
- `idx_actions_user_id` - Fast user action lookups
- `idx_actions_session_id` - Fast session action lookups
- `idx_actions_target_date` - Fast date filtering
- `idx_actions_user_target_date` - Composite index for dashboard queries

**contributions table:**
- `idx_contributions_session_id` - Fast session lookups
- `idx_contributions_round_number` - Fast round filtering

**votes table:**
- `idx_votes_session_id` - Fast session lookups

**audit_log table:**
- `idx_audit_log_user_id` - Fast user audit logs
- `idx_audit_log_timestamp` - Fast date filtering
- `idx_audit_log_resource` - Fast resource lookups

### Index Performance

With small datasets (<1000 rows):
- Index overhead is minimal
- PostgreSQL may choose Seq Scan over Index Scan (this is expected and optimal)

With large datasets (>10,000 rows):
- Indexes provide 10-100x speedup
- Critical for production performance
- Without indexes: 50-500ms per query
- With indexes: 0.5-5ms per query

### Verification Scripts

Check which indexes exist:
```bash
python scripts/verify_indexes.py
```

View query execution plans:
```bash
python scripts/explain_queries.py
```

Benchmark query performance:
```bash
python scripts/benchmark_indexes.py
```

## Production Deployment

Migrations are automatically run during blue-green deployment:

1. GitHub Actions builds Docker images
2. SSH into server, deploy to opposite environment
3. Run health checks
4. **Run migrations: `alembic upgrade head`**
5. Switch nginx config
6. Reload nginx

If migrations fail, deployment aborts and old environment stays active.

## Troubleshooting

**Error: "alembic_version table does not exist"**
- No migrations have been run yet
- Solution: `uv run alembic upgrade head`

**Error: "Can't locate revision identified by 'xyz'"**
- Migration history is out of sync
- Solution: Check `alembic_version` table, stamp correct version

**Error: "Target database is not up to date"**
- Pending migrations need to be applied
- Solution: `uv run alembic upgrade head`

**Error: "No changes detected"**
- Auto-generate didn't find model changes
- Solution: Create manual migration with `alembic revision -m "description"`
