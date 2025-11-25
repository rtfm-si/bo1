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
uv run alembic upgrade head

# Production Deploy (via GitHub Actions)
# Actions → "Deploy to Production" → Type "deploy-to-production"
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
- **Round Limit**: 6 rounds (down from 15)
- **Recursion Limit**: 20 steps (down from 55)
- **Experts per Round**: 3-5 (parallel execution via asyncio.gather)
- **Semantic Deduplication**: 0.80 similarity threshold (Voyage AI embeddings)
- **Hierarchical Context**: Round summaries + recent contributions
- **Feature Flag**: `ENABLE_PARALLEL_ROUNDS` (default: true)

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

### Optimizations (Jan 2025 Sprint)

- **LLM Response Caching**: 60% hit rate, Redis, 24h TTL
- **Persona Selection Caching**: Voyage AI embeddings, 40-60% hit rate
- **Database Connection Pooling**: Use `db_session()` context manager
- **Parallel async gather**: All expert calls simultaneous

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

## Key Files

- `bo1/graph/config.py` - Graph construction
- `bo1/graph/state.py` - State + conversions
- `bo1/graph/nodes.py` - Node implementations
- `bo1/graph/safety/loop_prevention.py` - Loop prevention
- `bo1/models/recommendations.py` - Recommendation models
- `bo1/state/postgres_manager.py` - DB operations
- `backend/api/main.py` - FastAPI entry
- `backend/api/streaming.py` - SSE endpoints (polling-based)
- `backend/api/middleware/auth.py` - SuperTokens auth
