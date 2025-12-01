# CLAUDE.md

Console-based AI system using multi-agent deliberation (Claude personas) for complex problem-solving.

**Status**: v2 production (https://boardof.one)

---

## System Flow

```
Problem → Decomposition → Persona Selection (3-5 experts) → Multi-Round Debate → Synthesis
```

**Architecture**: LangGraph state machine + Redis checkpointing + 5-layer loop prevention

---

## Key Commands

```bash
make up              # Start all services
make shell           # Container bash
make test            # Run tests
make pre-commit      # Lint + format + typecheck (RUN BEFORE PUSH)

# Migrations
uv run alembic upgrade head          # Apply all pending migrations
uv run alembic history               # View migration history
uv run alembic current               # Check current version
python scripts/check_migration_history.py  # Verify migrations applied

# Production Deploy (via GitHub Actions)
# Actions → "Deploy to Production" → Type "deploy-to-production"
# Migrations run automatically during deployment (see below)
```

---

## Feature Flags

**Active feature flags** (all others removed as unused):

### Authentication & Authorization
- **`ENABLE_SUPERTOKENS_AUTH`** (default: true)
  - When true: Full SuperTokens session verification required
  - When false: MVP mode with hardcoded test_user_1 (only if DEBUG=true)
  - Used in: `backend/api/middleware/auth.py`

### OAuth Providers
- **`GOOGLE_OAUTH_ENABLED`** (default: true)
  - Controls Google OAuth provider availability in SuperTokens
  - Used in: `backend/api/supertokens_config.py`

### Parallel Processing
- **`ENABLE_PARALLEL_ROUNDS`** (default: true)
  - When true: Multi-expert rounds run in parallel via `asyncio.gather`
  - When false: Experts contribute sequentially
  - Used in: `bo1/graph/nodes/subproblems.py`, `bo1/graph/config.py`

- **`ENABLE_PARALLEL_SUBPROBLEMS`** (default: false)
  - When true: Independent sub-problems execute concurrently (50-70% time reduction)
  - When false: Sequential execution (safer, better UX due to event emission issues)
  - Used in: `bo1/graph/nodes/subproblems.py`, `bo1/graph/config.py`
  - **Warning**: See Known Issues section - causes poor UX due to missing event emission

### Sub-Problem Deliberation
- **`USE_SUBGRAPH_DELIBERATION`** (default: false)
  - When true: Uses LangGraph subgraph with `get_stream_writer()` for real-time streaming
  - When false: Uses legacy `astream_events()` method
  - Used in: `backend/api/event_collector.py`
  - Requires: `ENABLE_PARALLEL_SUBPROBLEMS=true` to have effect

**Note**: Model selection (previously `FACILITATOR_MODEL`/`PERSONA_MODEL`) is now controlled via:
- `AI_OVERRIDE=true/false` in `.env`
- `AI_OVERRIDE_MODEL=<alias>` in `.env`
- See `bo1/config.py` for model aliases and role assignments

---

## Database Migrations

### Automatic Migration Deployment

**Migrations run automatically during production deployment** (Step 7 of blue-green deploy):

1. Check current migration version
2. Check for pending migrations
3. Apply migrations with `alembic upgrade head`
4. Verify final version
5. If migrations fail, deployment aborts and old environment stays active

**Key Features**:
- Runs AFTER health checks pass (safe environment)
- Runs BEFORE nginx cutover (no user impact)
- Full error logging to `/tmp/migration.log`
- Automatic rollback on failure
- Verification of critical tables post-migration

### Migration Types

**Alembic Migrations** (Preferred):
- Location: `migrations/versions/*.py`
- Managed by Alembic, tracked in `alembic_version` table
- Run with: `uv run alembic upgrade head`
- Create new: `uv run alembic revision -m "description"`

**SQL Migrations** (Legacy - Use Only If Needed):
- Location: `bo1/database/migrations/*.sql`
- For standalone SQL files not yet in Alembic
- Run with: `./scripts/run-sql-migrations.sh`
- Tracked in `sql_migrations` table

**IMPORTANT**: Always prefer Alembic migrations. SQL migrations should only be used for:
- Emergency hotfixes that can't wait for Alembic
- One-time data migrations that don't fit Alembic's schema-based approach

### Creating New Migrations

```bash
# Auto-generate from model changes (RECOMMENDED)
uv run alembic revision --autogenerate -m "add_new_table"

# Create empty migration (for data migrations)
uv run alembic revision -m "backfill_user_data"

# ALWAYS review auto-generated migrations before committing!
```

### Migration Safety Checklist

Before deploying migrations:

- [ ] Migration is idempotent (can run multiple times safely)
- [ ] Migration has both `upgrade()` and `downgrade()` functions
- [ ] Migration tested locally: `alembic upgrade head`
- [ ] Migration tested rollback: `alembic downgrade -1`
- [ ] No data loss (use ALTER TABLE IF NOT EXISTS, etc.)
- [ ] Backward compatible during blue-green switch
- [ ] Indexes added for new columns with frequent queries
- [ ] Comments added for complex migrations

### Troubleshooting Migrations

**Migration fails during deployment**:
- Deployment automatically aborts
- Old environment stays active (zero downtime)
- Check GitHub Actions logs for error details
- Check `/tmp/migration.log` on server
- Fix migration locally, test, then redeploy

**Check migration status in production**:
```bash
ssh deploy@server
docker exec boardofone-api-1 uv run alembic current
docker exec boardofone-api-1 uv run alembic history
```

**Manually run migrations (emergency only)**:
```bash
ssh deploy@server
docker exec -it boardofone-api-1 uv run alembic upgrade head
```

---

## Architecture

### LangGraph State Machine

```
decompose_node → select_personas_node → initial_round_node
  → facilitator_decide_node → (parallel_round_node | persona_contribute_node | moderator_intervene_node)
  → check_convergence_node → (loop back OR vote_node) → synthesize_node → END
```

**Parallel Multi-Expert Architecture** (Day 38+):
- **Round Limit**: 3-6 rounds (adaptive based on complexity)
- **Recursion Limit**: 20 steps (down from 55)
- **Experts per Round**: 3-5 (adaptive, parallel execution via asyncio.gather)
- **Semantic Deduplication**: 0.80 similarity threshold (Voyage AI embeddings)
- **Hierarchical Context**: Round summaries + recent contributions
- **Feature Flags**:
  - `ENABLE_PARALLEL_ROUNDS` (default: true) - Multi-expert rounds run in parallel
  - `ENABLE_PARALLEL_SUBPROBLEMS` (default: false) - Sub-problems execute concurrently (see Known Issues)
  - `USE_SUBGRAPH_DELIBERATION` (default: false) - LangGraph subgraph for real-time event streaming

**Adaptive Complexity Scoring** (NEW):
- **Complexity Assessment**: 5-dimension scoring (scope, dependencies, ambiguity, stakeholders, novelty)
- **Adaptive Rounds**: 3 rounds for simple problems, 6 for complex strategic decisions
- **Adaptive Experts**: 3 experts for focused problems, 5 for diverse perspectives
- **Time Savings**: 30-50% reduction on simple problems, full depth on complex ones
- **See**: `COMPLEXITY_SCORING.md` for detailed documentation

**Phase-Based Deliberation**:
- **Exploration** (rounds 1-2): Divergent thinking, surface all perspectives
- **Challenge** (rounds 3-4): Deep analysis with evidence, challenge weak arguments
- **Convergence** (rounds 5-6): Synthesis, explicit recommendations

**Key files**:
- `bo1/graph/config.py` - Graph construction
- `bo1/graph/state.py` - State definition + v1 conversion
- `bo1/graph/nodes.py` - Node implementations (parallel_round_node)
- `bo1/graph/quality/semantic_dedup.py` - Semantic deduplication
- `bo1/graph/safety/loop_prevention.py` - Loop prevention (6 round hard cap)

### Recommendation System (NOT Voting)

**CRITICAL**: Use recommendations (free-form), NOT binary votes.

- `Recommendation` model - `recommendation` field (string), NOT `decision` enum
- Use `collect_recommendations()` NOT `collect_votes()`
- Use `aggregate_recommendations_ai()` NOT `aggregate_votes_ai()`
- Prompt: `RECOMMENDATION_SYSTEM_PROMPT` with `<recommendation>` XML tags

- Personas: `bo1/data/personas.json` (45 experts)
- Prompts: `bo1/prompts/reusable_prompts.py`
- Models: `bo1/models/recommendations.py`
- Sonnet 4.5 with prompt caching (90% savings)
- Haiku 4.5 for summarization
- Cost target: ~$0.10 per deliberation

### Model Selection

**Model selection is controlled via `bo1/config.py`**:
- `AI_OVERRIDE=true/false` - Override all model calls with cheaper model (for testing)
- `AI_OVERRIDE_MODEL=<model_alias>` - Which model to use when override is enabled
- Aliases: `sonnet`, `haiku`, `opus` (see `MODEL_ALIASES` in config.py)

**Default models by role** (when `AI_OVERRIDE=false`):
- Personas: Sonnet 4.5 (benefits from prompt caching)
- Facilitator: Sonnet 4.5 (complex orchestration decisions)
- Summarizer: Haiku 4.5 (simple compression task)
- Decomposer: Sonnet 4.5 (complex problem analysis)

### Optimizations

- **Database Connection Pooling**: Use `db_session()` context manager
- **Parallel async gather**: All expert calls simultaneous via `asyncio.gather`
- **Prompt Caching**: Sonnet 4.5 with prompt caching (90% savings on cache hits)

### Loop Prevention

5-layer system prevents infinite loops:
1. Recursion limit (20 steps, down from 55)
2. Cycle detection (compile-time)
3. Round counter (6 max, down from 15)
4. Timeout watchdog (1 hour)
5. Cost kill switch (tier-based)

---

## Production Architecture

**Blue-Green Deployment**:
- Shared infra: postgres, redis, supertokens (`docker-compose.infrastructure.yml`)
- Blue/Green apps: api, frontend (`docker-compose.app.yml`)
- nginx routes traffic, serves static assets from `/var/www/boardofone/static-{env}/`

**Container Communication** (use Docker hostnames, NOT localhost):
- `postgres:5432`
- `redis:6379`
- `supertokens:3567`

**Frontend Env Vars**:
- Use `$env/dynamic/public` for runtime resolution (NOT `import.meta.env`)
- `PUBLIC_API_URL` resolved at runtime

---

## Critical Patterns

### Database

```python
from bo1.state.postgres_manager import db_session

# ALWAYS use context manager
with db_session() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM table WHERE id = %s", (id,))
```

### State Conversion

```python
from bo1.graph.state import state_to_v1, v1_to_state

v1_state = state_to_v1(graph_state)  # For agent calls
graph_state = v1_to_state(v1_state)  # For graph updates
```

---

## What NOT to Do

- ❌ Use `collect_votes()` → ✅ Use `collect_recommendations()`
- ❌ Binary voting/`VoteDecision` enum → ✅ Free-form recommendations
- ❌ `import.meta.env` → ✅ `$env/dynamic/public`
- ❌ `localhost` in containers → ✅ Docker service names
- ❌ Manual `conn.commit()` → ✅ `db_session()` context manager
- ❌ Proxy static assets through Node → ✅ nginx serves directly

---

## Known Issues & Implementation Plans

**⚠️ Parallel Sub-Problems Event Emission (High Priority)**
- **Problem**: Users see no UI updates for 3-5 minutes during parallel deliberation (appears stuck/failed)
- **Root Cause**: `_deliberate_subproblem()` doesn't emit real-time events to SSE stream
- **Impact**: Poor UX - users think meeting failed when it's actually running
- **Plan**: See `PARALLEL_SUBPROBLEMS_EVENT_EMISSION_FIX.md` for detailed implementation plan
- **Workaround**: Set `ENABLE_PARALLEL_SUBPROBLEMS=false` for better UX (loses 50-70% speed)
- **Estimated Fix**: 8-12 hours (EventBridge pattern)

---

## Recent Audit Fixes (2025-12-01)

**Comprehensive fixes implemented from MEETING_SYSTEM_AUDIT_REPORT.md**:

### Priority 1: Critical UX Fixes (COMPLETED)
1. **USE_SUBGRAPH_DELIBERATION enabled** - Already active in `.env`, provides real-time event streaming during parallel sub-problems (eliminates 3-5 min UI blackouts)
2. **Duplicate event emission removed** - `event_collector.py:569-596` converted to no-op to prevent duplicate "Sub-Problem Complete" messages
3. **Premature meta-synthesis prevention** - `routers.py:128-177` now validates ALL sub-problems completed before meta-synthesis, emits `meeting_failed` event if any sub-problems fail

### Priority 2: "Still Working" Messages (COMPLETED)
1. **WorkingStatus component created** - `frontend/src/lib/components/ui/WorkingStatus.svelte` provides sticky, prominent status indicator with elapsed time
2. **Working status events emitted** - `event_collector.py` now emits `working_status` events before:
   - Voting phase
   - Synthesis phase
   - Each parallel round
   - Meta-synthesis phase
3. **WorkingStatus integrated** - Meeting page (`frontend/src/routes/(app)/meeting/[id]/+page.svelte`) displays WorkingStatus component, clears on event completion

**Impact**:
- Zero UI blackouts (continuous updates every 5-10s)
- No duplicate event messages
- No incomplete syntheses
- Prominent working status at all times
- Better user experience during long operations

**Next Priorities** (Priority 3-5 pending):
- Hierarchical summarization (use round summaries in synthesis)
- Display expert summaries in UI
- Graph simplification (remove rarely-used nodes)
- Decomposition improvements (fewer, more relevant sub-problems)

---

## Key Files

- `bo1/graph/config.py` - Graph construction
- `bo1/graph/state.py` - State + conversions
- `bo1/graph/nodes.py` - Node implementations
- `bo1/graph/safety/loop_prevention.py` - Loop prevention
- `bo1/models/recommendations.py` - Recommendation models
- `bo1/state/postgres_manager.py` - DB operations
- `backend/api/main.py` - FastAPI entry
- `backend/api/streaming.py` - SSE endpoints (polling-based)
- `backend/api/event_publisher.py` - Event publishing (Redis + PostgreSQL)
- `backend/api/event_collector.py` - Wraps graph execution, emits events
- `backend/api/middleware/auth.py` - SuperTokens auth
