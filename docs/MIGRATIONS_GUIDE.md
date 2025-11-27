# Database Migrations Guide

Comprehensive guide for managing database migrations in Board of One.

---

## Table of Contents

1. [Overview](#overview)
2. [Automatic Deployment](#automatic-deployment)
3. [Creating Migrations](#creating-migrations)
4. [Testing Migrations](#testing-migrations)
5. [Production Workflow](#production-workflow)
6. [Emergency Procedures](#emergency-procedures)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Board of One uses **Alembic** for database schema migrations. Migrations run automatically during production deployment with zero downtime.

### Migration Types

**Alembic Migrations (Primary)**:
- Location: `migrations/versions/*.py`
- Tracking: `alembic_version` table
- Use for: Schema changes, indexes, constraints

**SQL Migrations (Legacy)**:
- Location: `bo1/database/migrations/*.sql`
- Tracking: `sql_migrations` table
- Use for: Emergency hotfixes only

**Recommendation**: Always use Alembic migrations. SQL migrations are for exceptional cases only.

---

## Automatic Deployment

### How It Works

Migrations run automatically during production deployment (Step 7 of blue-green deploy):

```bash
# Deployment sequence
1. Build Docker images
2. Deploy to opposite environment (blue/green)
3. Start containers
4. Health checks (API, DB, Redis)
5. Extract static assets
6. 🗄️  RUN MIGRATIONS (automatic)
7. Switch nginx to new environment
8. Verify deployment
9. Stop old environment
```

### Migration Process

When deployment reaches Step 7:

```bash
# 1. Check current version
$ alembic current
Current revision: f23423398b2a

# 2. Check for pending migrations
$ alembic history --verbose
# Shows migration chain and pending changes

# 3. Apply migrations
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade f23423398b2a -> 622dbc22743e, add_session_events_and_tasks_tables
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.

# 4. Verify final version
$ alembic current
Current revision: 622dbc22743e (head)

# 5. Verify critical tables
$ psql -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
```

### Safety Features

**Automatic Failure Handling**:
- Migration fails → Deployment aborts
- Old environment stays active
- Full error logs in GitHub Actions
- No user impact

**Rollback Strategy**:
- Blue-green architecture allows instant rollback
- Simply switch nginx back to old environment
- Database can be rolled back with `alembic downgrade -1`

**Why This Timing**:
- Migrations run AFTER health checks (safe environment)
- Migrations run BEFORE nginx cutover (no user traffic yet)
- Zero downtime, zero user impact

---

## Creating Migrations

### Method 1: Auto-generate from Models (Recommended)

```bash
# 1. Make model changes in your code
# Example: Add new column to bo1/models/user.py

# 2. Auto-generate migration
uv run alembic revision --autogenerate -m "add_user_preferences"

# 3. Review generated migration
cat migrations/versions/XXXX_add_user_preferences.py

# 4. Edit if needed (Alembic doesn't catch everything)
# - Add indexes
# - Add comments
# - Add data migrations
# - Fix edge cases

# 5. Test locally
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```

### Method 2: Manual Migration

```bash
# 1. Create empty migration
uv run alembic revision -m "backfill_user_data"

# 2. Edit migration file
# migrations/versions/XXXX_backfill_user_data.py

def upgrade() -> None:
    """Backfill user data."""
    # Add your migration logic
    op.execute("""
        UPDATE users
        SET preferences = '{}'::jsonb
        WHERE preferences IS NULL;
    """)

def downgrade() -> None:
    """Rollback backfill."""
    # Add rollback logic
    pass
```

### Migration Template

```python
"""Short description of migration

Detailed explanation of what this migration does and why.

Revision ID: abc123def456
Revises: xyz789
Create Date: 2025-01-27 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = 'xyz789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema changes."""

    # Create table with IF NOT EXISTS for idempotency
    op.create_table(
        'new_table',
        sa.Column('id', sa.BigInteger(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('data', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes
    op.create_index('idx_new_table_user_id', 'new_table', ['user_id'])

    # Add comments
    op.execute("""
        COMMENT ON TABLE new_table IS 'Description of table purpose';
        COMMENT ON COLUMN new_table.user_id IS 'Reference to users table';
    """)


def downgrade() -> None:
    """Rollback schema changes."""

    op.drop_index('idx_new_table_user_id', table_name='new_table')
    op.drop_table('new_table')
```

---

## Testing Migrations

### Local Testing

```bash
# 1. Start local database
make up

# 2. Apply migration
uv run alembic upgrade head

# 3. Test application
make test

# 4. Test rollback
uv run alembic downgrade -1

# 5. Re-apply to test idempotency
uv run alembic upgrade head
uv run alembic upgrade head  # Should be no-op

# 6. Check migration history
uv run alembic history
uv run alembic current

# 7. Verify database schema
python scripts/check_migration_history.py
```

### Testing Checklist

Before committing a migration:

- [ ] Migration is idempotent (can run multiple times)
- [ ] Both `upgrade()` and `downgrade()` implemented
- [ ] Tested locally: `alembic upgrade head`
- [ ] Tested rollback: `alembic downgrade -1`
- [ ] Tested re-apply: `alembic upgrade head` (twice)
- [ ] No data loss (IF NOT EXISTS, etc.)
- [ ] Backward compatible during blue-green
- [ ] Indexes added for queried columns
- [ ] Comments added for documentation
- [ ] Application still works with new schema
- [ ] Tests pass: `make test`

---

## Production Workflow

### Standard Deployment

```bash
# 1. Create migration locally
uv run alembic revision --autogenerate -m "add_feature"

# 2. Test thoroughly
uv run alembic upgrade head
make test
uv run alembic downgrade -1
uv run alembic upgrade head

# 3. Commit and push
git add migrations/versions/*.py
git commit -m "feat: add feature migration"
git push origin main

# 4. Deploy via GitHub Actions
# Go to: Actions → "Deploy to Production"
# Type: "deploy-to-production"

# 5. Monitor deployment
# Watch GitHub Actions logs for migration output
# Check for: "✅ Migrations completed successfully"

# 6. Verify in production
ssh deploy@server
docker exec boardofone-api-1 uv run alembic current
```

### What Gets Deployed

```
Deployment includes:
✅ All new Alembic migrations in migrations/versions/
✅ Automatic execution via alembic upgrade head
✅ Full logging and error handling
✅ Automatic verification of critical tables
✅ Automatic rollback on failure
```

---

## Emergency Procedures

### Migration Failed During Deployment

**Symptom**: GitHub Actions shows migration error

**Action**:
1. Deployment automatically aborts
2. Old environment stays active (users unaffected)
3. Check error logs in GitHub Actions
4. Fix migration locally
5. Test fix thoroughly
6. Redeploy

```bash
# Example: Migration fails due to syntax error
# 1. GitHub Actions shows: "❌ Migration failed!"
# 2. Old environment continues serving traffic
# 3. Check logs:
echo "Error in migration 622dbc22743e: syntax error..."

# 4. Fix migration locally
vim migrations/versions/622dbc22743e_fix.py

# 5. Test fix
uv run alembic upgrade head

# 6. Redeploy
git commit -m "fix: migration syntax error"
git push
# Run GitHub Actions deployment again
```

### Manual Migration in Production (Emergency Only)

**Use Case**: Critical hotfix can't wait for full deployment

```bash
# 1. SSH to production
ssh deploy@server

# 2. Check current version
docker exec boardofone-api-1 uv run alembic current

# 3. Run migration
docker exec -it boardofone-api-1 uv run alembic upgrade head

# 4. Verify
docker exec boardofone-api-1 uv run alembic current

# 5. Monitor logs
docker logs boardofone-api-1 -f
```

**IMPORTANT**: Always follow up with proper deployment to update both blue and green environments.

### Rollback Migration

**Symptom**: Migration succeeded but caused application issues

```bash
# 1. SSH to production
ssh deploy@server

# 2. Rollback one migration
docker exec -it boardofone-api-1 uv run alembic downgrade -1

# 3. Verify rollback
docker exec boardofone-api-1 uv run alembic current

# 4. Restart application
docker-compose -f docker-compose.app.yml -p boardofone restart api

# 5. Monitor
docker logs boardofone-api-1 -f
```

### Stuck Migration

**Symptom**: Migration hangs indefinitely

```bash
# 1. Kill hanging migration
docker exec boardofone-api-1 pkill -9 alembic

# 2. Check database locks
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "
SELECT pid, state, query
FROM pg_stat_activity
WHERE state = 'active' AND query LIKE '%ALTER TABLE%';"

# 3. Kill blocking queries (if safe)
# docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "SELECT pg_terminate_backend(PID);"

# 4. Check migration state
docker exec boardofone-api-1 uv run alembic current

# 5. If needed, manually mark migration as complete
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "
UPDATE alembic_version SET version_num = 'TARGET_REVISION';"
```

---

## Best Practices

### Do's ✅

1. **Always use Alembic** for schema changes
2. **Make migrations idempotent** (IF NOT EXISTS, IF EXISTS)
3. **Test locally** before pushing
4. **Add comments** to tables and columns
5. **Create indexes** for frequently queried columns
6. **Keep migrations small** (one logical change per migration)
7. **Use transactions** (Alembic does this automatically for Postgres)
8. **Document complex migrations** in docstring
9. **Backward compatible** during blue-green deployment
10. **Monitor after deployment** (check logs, verify data)

### Don'ts ❌

1. **Don't run migrations manually** in production (except emergencies)
2. **Don't skip testing** locally
3. **Don't make destructive changes** without backup strategy
4. **Don't use raw SQL** unless necessary (use op.create_table, etc.)
5. **Don't forget downgrade()** function
6. **Don't commit broken migrations**
7. **Don't mix schema and data changes** (separate migrations)
8. **Don't ignore warnings** during autogenerate
9. **Don't modify existing migrations** (create new ones)
10. **Don't forget to test rollback**

### Idempotency Patterns

```python
# ✅ Good: Idempotent table creation
op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(255) PRIMARY KEY,
        email VARCHAR(255) NOT NULL
    );
""")

# ❌ Bad: Non-idempotent (fails on re-run)
op.create_table('users', ...)

# ✅ Good: Idempotent column addition
op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'preferences'
        ) THEN
            ALTER TABLE users ADD COLUMN preferences JSONB;
        END IF;
    END
    $$;
""")

# ✅ Good: Idempotent index creation
op.create_index('idx_users_email', 'users', ['email'], unique=True, if_not_exists=True)
```

### Backward Compatibility

```python
# ✅ Good: Add column with default (backward compatible)
op.add_column('users', sa.Column('preferences', JSONB, server_default='{}'))

# ❌ Bad: Add NOT NULL column without default (breaks old code)
op.add_column('users', sa.Column('preferences', JSONB, nullable=False))

# ✅ Good: Two-step migration for NOT NULL
# Migration 1: Add nullable column with default
op.add_column('users', sa.Column('preferences', JSONB, nullable=True, server_default='{}'))

# Migration 2 (later): Backfill data, then make NOT NULL
op.execute("UPDATE users SET preferences = '{}' WHERE preferences IS NULL;")
op.alter_column('users', 'preferences', nullable=False)
```

---

## Troubleshooting

### Common Issues

**Error: "alembic_version table does not exist"**
```bash
# No migrations have been run yet
uv run alembic upgrade head
```

**Error: "Can't locate revision identified by 'xyz'"**
```bash
# Migration history out of sync
# Check current version
docker exec boardofone-api-1 uv run alembic current

# Check what version is in database
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "SELECT * FROM alembic_version;"

# Manually stamp to correct version (CAREFUL!)
uv run alembic stamp <revision>
```

**Error: "Target database is not up to date"**
```bash
# Pending migrations need to be applied
uv run alembic upgrade head
```

**Error: "Multiple head revisions present"**
```bash
# Migration branch conflict - need to merge
uv run alembic merge -m "merge heads" <rev1> <rev2>
```

**Error: "column already exists"**
```bash
# Migration not idempotent - add IF NOT EXISTS checks
# See idempotency patterns above
```

### Debugging Commands

```bash
# Check migration history
uv run alembic history

# Check current version
uv run alembic current

# Show pending migrations
uv run alembic history --verbose | grep "-> head"

# Show all tables
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "\dt"

# Show table schema
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "\d users"

# Check migration tracking table
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "SELECT * FROM alembic_version;"

# Verify specific table exists
python scripts/check_migration_history.py
```

### Production Health Check

```bash
# 1. Check current migration version
ssh deploy@server
docker exec boardofone-api-1 uv run alembic current

# 2. Compare with expected version (from git)
git log --oneline migrations/versions/ | head -1

# 3. Verify critical tables exist
docker exec infrastructure-postgres-1 psql -U bo1 -d boardofone -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;"

# 4. Check for migration errors in logs
docker logs boardofone-api-1 | grep -i migration

# 5. Test database connectivity
curl https://boardof.one/api/health/db
```

---

## Resources

- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Project Migrations**: `/migrations/versions/`
- **Migration README**: `/migrations/README.md`
- **CLAUDE.md**: Database Migrations section

---

## Migration History

Recent migrations (newest first):

1. `622dbc22743e` - Add session_events and session_tasks tables
2. `001_research_metrics` - Add research metrics table
3. `f23423398b2a` - Fix research cache vector type and index
4. `9f3c7b8e2d1a` - Add waitlist table
5. `8a5d2f9e1b3c` - Add beta whitelist
6. `71a746e3c1d9` - Add context tables
7. `2f7e9d4c8b1a` - Add actions lite
8. `ced8f3f148bb` - Initial schema

Full history: `uv run alembic history`
