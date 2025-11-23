# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project: Board of One (bo1)

Console-based AI system using multi-agent deliberation (Claude personas) to solve complex problems through structured debate and synthesis.

**Status**: v2 deployed to production (https://boardof.one)

**Note on SSE Streaming**: Current web implementation uses polling-based event detection (2-second intervals). A comprehensive plan for full real-time streaming via LangGraph `astream_events()` + Redis PubSub is documented in `STREAMING_IMPLEMENTATION_PLAN.md` at project root.

---

## System Flow

```
Problem → Decomposition (1-5 sub-problems) → Persona Selection (3-5 experts)
→ Multi-Round Debate → Recommendations → Synthesis → Final Output
```

**Architecture**: LangGraph-based state machine with Redis checkpointing, 5-layer loop prevention, and AI-powered synthesis.

---

## Commands (Docker-First Workflow)

```bash
# Setup (one-time)
make setup           # Creates .env, directories
make build           # Build Docker images
make up              # Start all services (Redis + PostgreSQL + API + SuperTokens + Frontend + app)

# Development
make run             # Run deliberation (interactive)
make demo            # Run full pipeline demo
make shell           # Bash in container
make shell-frontend  # Shell in frontend container
make logs            # View all container logs
make logs-app        # View app logs only
make logs-api        # View API logs only
make logs-frontend   # View frontend logs only

# Testing
make test            # All tests in container
make test-unit       # Unit tests only
make test-integration # Integration tests only
make test-coverage   # Generate HTML coverage report

# Code Quality (Before Pushing)
make pre-commit      # Full suite: lint + format + typecheck (RUN BEFORE GIT PUSH)
make fix             # Auto-fix linting and formatting issues
make lint            # ruff check
make format          # ruff format
make typecheck       # mypy

# Redis
make redis-cli       # Open Redis CLI
make redis-ui        # Web UI (http://localhost:8081)
make backup-redis    # Backup Redis data to ./backups/
make clean-redis     # Clear all Redis data (WARNING: deletes everything)

# Debugging
make status          # Show container status
make stats           # Show resource usage
make inspect         # View container configuration

# Web Interface
# Frontend runs automatically with `make up` on http://localhost:5173
# API runs automatically with `make up` on http://localhost:8000
# Access admin docs: http://localhost:8000/admin/docs (requires admin auth)
# SuperTokens Core: http://localhost:3567

# Production Deployment (Blue-Green)
# See docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md for complete setup guide
# See docs/BLUE_GREEN_DEPLOYMENT.md for deployment flow details

# Initial Server Setup (one-time)
bash deployment-scripts/setup-production-server.sh      # Configure server (Docker, nginx, deploy user)
bash deployment-scripts/setup-github-ssh-keys.sh        # Generate SSH keys for GitHub Actions
bash deployment-scripts/verify-server-setup.sh          # Verify server configuration

# SSL Certificates (Automated)
# Let's Encrypt certificates are automatically obtained during first deployment
# Auto-renewal via certbot.timer (every 60 days)
# Manual setup: bash deployment-scripts/setup-letsencrypt.sh

# Deploy (via GitHub Actions)
# Go to Actions tab → "Deploy to Production" → Run workflow → Type "deploy-to-production"
# Blue-green deployment: Zero downtime, automatic rollback, preserves active sessions
# First deployment automatically sets up Let's Encrypt SSL certificates
```

**Hot Reload**: Edit code locally, changes immediately available in container (no rebuild).

**Database Migrations (Alembic)**:
```bash
# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history

# Create new migration
uv run alembic revision -m "description"

# Verify indexes
python scripts/verify_indexes.py

# Check query execution plans
python scripts/explain_queries.py
```

**Database Indexes**: All critical tables have performance indexes for fast queries. Indexes provide 10-100x speedup on large datasets (>10K rows). See `migrations/README.md` for complete index documentation.

**Local Development**: For running tests locally (outside Docker):
```bash
# Requires: Redis + PostgreSQL running locally, .env configured, uv sync completed
pytest                              # All tests
pytest -m unit                      # Unit tests only
pytest -m "not requires_llm"        # Skip LLM tests (faster)
pytest tests/path/to/test.py::test_name -v  # Single test
ruff check . && ruff format --check . && mypy bo1/   # Pre-commit checks
```

---

## Architecture

### LangGraph State Machine

Board of One uses **LangGraph** (not plain LangChain) for stateful orchestration:

```
decompose_node → select_personas_node → initial_round_node
  → facilitator_decide_node → (persona_contribute_node | moderator_intervene_node)
  → check_convergence_node → (loop back OR vote_node)
  → synthesize_node → END
```

**Key files**:
- `bo1/graph/config.py` - Graph construction and compilation
- `bo1/graph/state.py` - TypedDict state definition + conversion to/from v1 models
- `bo1/graph/nodes.py` - Node implementations (decompose, contribute, vote, etc.)
- `bo1/graph/routers.py` - Conditional edge routing logic
- `bo1/graph/safety/loop_prevention.py` - 5-layer loop prevention system

**State management**:
- LangGraph uses `DeliberationGraphState` (TypedDict) for graph execution
- v1 models (`DeliberationState`, Pydantic) still used internally by agents
- Conversion functions: `state_to_v1()` and `v1_to_state()` bridge the gap

### Recommendation System (NOT Binary Voting)

**IMPORTANT**: The system uses **flexible recommendations**, not binary yes/no votes.

**Migration completed** (2025-01-15): Voting system replaced with recommendation system to support both:
- Binary questions: "Should we invest in X?" → "Yes, invest" OR "No, invest in Y instead"
- Strategy questions: "What compensation structure?" → "60% salary, 40% dividends"

**Key models**:
- `Recommendation` (replaces `Vote`) - `recommendation` field (free-form string), NOT `decision` enum
- `RecommendationAggregation` (replaces `VoteAggregation`) - AI-synthesized consensus
- Legacy aliases: `Vote` and `VoteAggregation` exist for backward compatibility ONLY

**Prompts**:
- Use `RECOMMENDATION_SYSTEM_PROMPT` (NOT `VOTING_SYSTEM_PROMPT`)
- XML tags: `<recommendation>`, `<reasoning>`, `<confidence>`, `<conditions>`
- NO keyword matching - recommendations stored as-is from experts

**Functions**:
- `collect_recommendations()` (NOT `collect_votes()`)
- `aggregate_recommendations_ai()` (NOT `aggregate_votes_ai()`)
- Response parser: `parse_recommendation_from_response()` - extracts from XML, no keyword logic

### Prompt Engineering (Critical)

All prompts follow the Prompt Engineering Framework (documented in zzz_important/):
- **XML structure** with `<thinking>`, `<contribution>`, `<recommendation>` tags
- **Modular composition**: Bespoke persona identity + generic protocols + dynamic context
- Personas stored in `bo1/data/personas.json` (45 experts)
- Generic protocols in `bo1/prompts/reusable_prompts.py`

**Cost Optimization**:
- Use **Sonnet 4.5 with prompt caching** for personas (90% cheaper than naive)
- Use **Haiku 4.5** for summarization (background agent)
- Hierarchical context: Old rounds = 100-token summaries, current round = full messages
- Target: ~$0.10 per deliberation (35 persona calls + 6 summaries)

**Performance Optimizations** (2025-01-23 Refactoring):
- **Parallel Recommendation Collection**: Async gather for 5 experts (75% faster than sequential)
- **Persona Data Caching**: LRU cache on `load_personas()` (eliminates 100+ file reads per session)
- **Database Connection Pooling**: ThreadedConnectionPool (min=1, max=20) prevents connection exhaustion
- **API Response Compression**: GZip middleware (60-80% bandwidth reduction for JSON responses)

### Context Management (Prevents Quadratic Growth)

```python
# Previous rounds: Summarized (cached)
round_summaries: list[str]  # 100 tokens each

# Current round: Full detail (uncached)
current_round_contributions: list[dict]  # ~200 tokens each

# Total context: ~1,400 tokens (linear growth, not quadratic)
```

**Summarizer Agent**: Runs in background (asyncio) while next round proceeds. Zero latency impact.

### Consensus Mechanisms

- **Convergence detection**: Semantic similarity >0.85, novelty <0.3 → early stop
- **Adaptive rounds**: Simple (5 max), Moderate (7), Complex (10), Hard cap (15)
- **Problem drift detection**: #1 failure cause - check relevance every contribution
- **Facilitator orchestration**: Sequential decisions (continue/vote/research/moderator/clarify)

### Human-in-the-Loop Context Collection (Week 6)

Board of One collects context at **3 strategic points** to improve deliberation quality:

1. **Business Context** (pre-decomposition, persistent, optional)
   - Collected once, reused across sessions
   - Stored in `user_context` table (PostgreSQL)
   - Fields: business_model, target_market, revenue, growth_rate, competitors
   - User can update anytime via profile or `--update-context` flag

2. **Information Gaps** (post-decomposition, problem-specific)
   - AI identifies CRITICAL vs NICE_TO_HAVE questions via `identify_information_gaps()`
   - INTERNAL gaps: User-only knowledge (churn rate, CAC, etc.) → prompt user
   - EXTERNAL gaps: Researchable data (industry benchmarks) → auto-filled via web search
   - User can skip any question (reduces confidence, doesn't block)

3. **Expert Clarification** (mid-deliberation, blocking questions)
   - Facilitator action="clarify" pauses deliberation
   - User options: Answer now / Pause session / Skip
   - If paused: Checkpoint saved, user resumes later with `--resume <session_id>`
   - Answers injected into `problem.context` and logged in `session_clarifications` table

**Key Design Principles**:
- **Optional but encouraged**: "Adding context improves recommendations by 40%"
- **Persistence prevents re-asking**: Business context saved across sessions
- **Pause/resume for blocking questions**: User can gather info offline
- **User sovereignty**: Can skip any question (system adapts, doesn't block)

**Implementation**: See zzz_project/detail/CONTEXT_COLLECTION_FEATURE.md (not tracked in git)

### External Research Cache with Embeddings (Week 6)

Board of One caches external research results with semantic similarity matching to reduce costs by 70-90%.

**Architecture**:
- **Storage**: PostgreSQL `research_cache` table with pgvector embeddings
- **Embeddings**: Voyage AI voyage-3 (1024 dimensions, ~$0.00006 per query)
- **Similarity Matching**: Cosine similarity threshold 0.85
- **Freshness Policy**: Category-based (saas_metrics: 90 days, pricing: 180 days, competitor_analysis: 30 days)

**Cache Flow**:
1. Generate embedding for question (Voyage AI voyage-3)
2. Semantic search in cache (pgvector cosine similarity)
3. If similarity >0.85 and fresh → return cached result (~50ms, $0.00006)
4. If cache miss → web search + summarization (~5-10s, $0.05-0.10) → save to cache

**Cost Reduction**:
- **Without cache**: 300 queries/month × $0.07 = $21.00/month
- **With cache (70% hit rate)**: $6.32/month (70% savings)
- **With cache (90% hit rate)**: $2.13/month (90% savings)
- **Voyage AI embeddings**: 10x cheaper than OpenAI ada-002 ($0.06/M tokens vs $0.10/M tokens)

**Example Cache Hits**:
- "What is average churn rate for B2B SaaS?" (original)
- "Average monthly churn for SaaS companies?" (90% similar → cache hit)
- "Typical SaaS churn rate benchmarks?" (92% similar → cache hit)

**Implementation**: See zzz_project/detail/RESEARCH_CACHE_SPECIFICATION.md (not tracked in git)

### Loop Prevention (100% Confidence Guarantee)

Board of One implements a **5-layer defense system** to guarantee deliberations cannot loop indefinitely:

1. **Recursion Limit** (LangGraph built-in): 55 steps max → `GraphRecursionError`
2. **Cycle Detection** (compile-time): Rejects graphs with uncontrolled cycles
3. **Round Counter** (domain logic): Hard cap at 15 rounds + user-configured max
4. **Timeout Watchdog** (runtime): 1-hour timeout kills long-running sessions
5. **Cost Kill Switch** (budget enforcement): Tier-based cost limits force early synthesis

**Combined guarantee**: Even if 4 layers fail, the 5th will stop the loop.

**IMPORTANT**: When modifying convergence logic in `bo1/graph/safety/loop_prevention.py`:
- `check_convergence_node()` must respect pre-set `metrics.convergence_score` (don't recalculate if already set)
- Convergence threshold: `convergence_score > 0.85 and round_number >= 3`
- Handle `None` values: `metrics.convergence_score if metrics and metrics.convergence_score is not None else 0.0`

---

## Key Files & Directories

- `bo1/data/personas.json` - 45 experts (ONLY bespoke `<system_role>`, 879 chars avg)
- `bo1/prompts/reusable_prompts.py` - Generic protocols (behavioral, evidence, communication)
- `bo1/models/recommendations.py` - Recommendation models (replaces votes.py)
- `bo1/graph/` - LangGraph nodes, routers, state, config, loop prevention, analytics
- `bo1/graph/analytics.py` - Cost analytics and phase breakdown (CSV/JSON export)
- `bo1/agents/context_collector.py` - Business context + information gap collection
- `bo1/agents/researcher.py` - External research with semantic cache (Week 6)
- `bo1/llm/embeddings.py` - Voyage AI voyage-3 embedding generation (Week 6)
- `bo1/state/postgres_manager.py` - PostgreSQL CRUD operations for context, research cache
- `bo1/interfaces/console.py` - Console adapter with pause/resume support
- `migrations/` - Alembic database migrations (schema versioning)
- `migrations/README.md` - Database migration guide and index documentation
- `backend/api/main.py` - FastAPI application entry point
- `backend/api/streaming.py` - SSE streaming endpoints (polling-based, see STREAMING_IMPLEMENTATION_PLAN.md)
- `backend/api/middleware/auth.py` - SuperTokens session verification middleware
- `backend/api/admin.py` - Admin-only endpoints (session monitoring, metrics)
- `docker-compose.prod.yml` - Production deployment configuration
- `STREAMING_IMPLEMENTATION_PLAN.md` - Complete plan for real-time event streaming (6-day implementation)
- `MVP_IMPLEMENTATION_ROADMAP.md` - 14-week roadmap (101 days)
- `docs/QUICKSTART.md` - Getting started guide
- `docs/DEMO.md` - Demo and validation guide
- `docs/DOCKER.md` - Docker development guide
- `docs/TESTING.md` - Testing guide and patterns
- `docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md` - Production deployment
- `docs/BLUE_GREEN_DEPLOYMENT.md` - Blue-green deployment details
- `docs/COMPANY_STRUCTURE.md` - Company structure and decision-making
- `deployment-scripts/PRODUCTION_ENV_SETUP.md` - Environment setup guide
- `exports/` - Generated deliberation outputs (JSON, markdown reports)
- `backups/` - Redis backup files (created by `make backup-redis`)

---

## Important Design Constraints

**Console (v1)**:
- LangGraph state machine with Redis checkpointing (7-day TTL)
- Pause/resume support via `--resume <session_id>` flag
- Phase-based cost tracking and analytics
- PostgreSQL for persistent storage (personas, sessions)
- Console UI with Rich formatting and phase cost tables

**Web API (v2 - deployed)**:
- FastAPI with SSE streaming (`backend/api/`) - currently polling-based, see STREAMING_IMPLEMENTATION_PLAN.md
- SuperTokens auth (BFF pattern, httpOnly cookies, OAuth support for Google/GitHub/LinkedIn)
- Admin-only API docs (`/admin/docs` requires X-Admin-Key or admin JWT)
- Public landing page at root (`/`)
- Endpoints: health, sessions, streaming, context, control, admin, auth
- Production compose file: `docker-compose.prod.yml`
- GZip compression middleware (60-80% bandwidth reduction, 2025-01-23)
- Standardized error handling via `@handle_api_errors` decorator (Week 1 Sprint Optimization)

**API Error Handling Pattern**:
- Use `@handle_api_errors("operation")` decorator on all endpoints
- Use `raise_api_error(error_type)` for common error cases
- Standard error types: redis_unavailable, session_not_found, unauthorized, forbidden, invalid_input, not_found
- All errors logged with operation context
- Consistent HTTP status codes across API (400, 401, 403, 404, 500)
- No stack traces leaked to clients (graceful error messages)

**Cost targets**:
- $0.10-0.15 per sub-problem deliberation
- 5-15 min per deliberation
- 60-70% cost reduction via prompt caching

**Feature Flags** (Sprint Optimizations):

Runtime configuration toggles for experimental features and optimizations:

1. **LLM Response Caching** (Week 1):
   - `ENABLE_LLM_RESPONSE_CACHE=true` - Enable Redis-backed response caching
   - `LLM_RESPONSE_CACHE_TTL_SECONDS=86400` - Cache TTL (default: 24 hours)
   - Cache hit rate: 60-70% in production
   - Cost savings: $0.04-0.08 per cache hit
   - Storage: Redis with SHA-256 keyed entries

2. **Persona Selection Caching** (Week 2):
   - `ENABLE_PERSONA_SELECTION_CACHE=true` - Enable semantic persona caching
   - Cache hit rate: 40-60% for similar problems
   - Cost savings: $200-400/month at 1000 deliberations
   - Uses Voyage AI embeddings for similarity matching

3. **Context Collection** (Week 6):
   - `ENABLE_CONTEXT_COLLECTION=true` - Enable business context gathering (default: enabled)
   - Improves recommendation quality by 40%
   - Collects: business model, market, revenue, competitors

4. **SSE Streaming Mode** (Future):
   - `ENABLE_SSE_STREAMING=true` - Enable real-time LangGraph streaming
   - Default: false (uses polling-based events)
   - See `STREAMING_IMPLEMENTATION_PLAN.md` for implementation details

**User sovereignty**:
- System provides recommendations, NOT directives
- "We recommend X" not "You must do X"

**Safety**:
- All personas refuse harmful/illegal/unethical requests
- Generic safety protocol in `reusable_prompts.py`

**Production Deployment** (Blue-Green):

**Architecture Overview:**
- **Host nginx** (traffic router) → Blue or Green environments
- **Shared infrastructure** (postgres, redis, supertokens) via `docker-compose.infrastructure.yml`
- **Blue/Green apps** (api, frontend) via `docker-compose.app.yml` with different project names
- **Static assets** served directly by nginx from `/var/www/boardofone/static-{blue|green}/`

**Container Projects:**
- Infrastructure: `infrastructure` (postgres-1, redis-1, supertokens-1)
- Blue app: `boardofone` (api-1, frontend-1)
- Green app: `boardofone-green` (green-api-1, green-frontend-1)

**Docker Network:**
- External network: `bo1-network` (shared by all containers)
- Inter-container communication via Docker hostnames:
  - `DATABASE_URL=postgresql://bo1:password@postgres:5432/boardofone` (NOT localhost)
  - `REDIS_URL=redis://:password@redis:6379/0` (NOT localhost)
  - `SUPERTOKENS_CONNECTION_URI=http://supertokens:3567` (NOT localhost)

**Static Asset Serving (Critical for Performance):**
- SvelteKit builds to `build/client/` in container
- Deployment script extracts via `docker cp` to `/var/www/boardofone/static-{env}/`
- nginx serves directly from filesystem (NOT proxied through Node.js):
  - `/_app/immutable/` → Static JS/CSS chunks (1-year cache, immutable)
  - `/_app/version.json` → Version manifest (5-minute cache)
  - `/logo.svg`, `/demo_meeting.jpg` → Root images (1-day cache)
- Connection limit: 100 for static assets (vs 30 for dynamic routes)
- Result: 50-100ms faster TTFB, ~30% reduced Node.js CPU usage

**nginx Configuration:**
- Two configs: `nginx-blue.conf` and `nginx-green.conf`
- Active config copied to `/etc/nginx/sites-available/boardofone` during deployment
- Upstream backends point to localhost ports:
  - Blue: `127.0.0.1:8000` (API), `127.0.0.1:3000` (Frontend)
  - Green: `127.0.0.1:8001` (API), `127.0.0.1:3001` (Frontend)
- SSL via Let's Encrypt (auto-renewed via certbot.timer)

**Deployment Flow:**
1. GitHub Actions builds Docker images, pushes to registry
2. SSH into server, detect current environment (blue/green)
3. Deploy to opposite environment (green if blue is active)
4. Extract static assets: `docker cp {project}-frontend-1:/app/build/client/. /var/www/boardofone/static-{env}/`
5. Run health checks (API, database, Redis)
6. Run database migrations (Alembic)
7. Switch nginx config to new environment
8. Reload nginx (zero downtime)
9. Stop old environment (after 5s grace period)

**Authentication (SuperTokens):**
- Shared SuperTokens Core container (infrastructure layer)
- Frontend uses SuperTokens Web SDK for session management
- BFF pattern: httpOnly cookies (NOT localStorage tokens)
- OAuth providers: Google (configured), GitHub/LinkedIn (ready)
- Session cookies: `sAccessToken`, `sRefreshToken` (httpOnly, secure, sameSite)
- Auth endpoints: `/api/auth/*` (proxied to FastAPI)

**Environment Variables:**
- **Build-time** (embedded in frontend bundle):
  - `PUBLIC_API_URL` (via Docker build arg) - DEPRECATED, use runtime
  - `VITE_GOOGLE_OAUTH_CLIENT_ID` (for OAuth button)
- **Runtime** (available via $env/dynamic/public):
  - `PUBLIC_API_URL` - Resolved at runtime in Node.js process
  - `ORIGIN` - SvelteKit origin for CSRF protection
- **IMPORTANT**: Frontend uses `$env/dynamic/public` for runtime resolution (NOT `import.meta.env`)

**Local vs Production Differences:**
- **Local** (docker-compose.yml):
  - All services in one compose file
  - Frontend on port 5173 (Vite dev server with HMR)
  - API on port 8000
  - No nginx (direct container access)
  - SQLite for local dev (optional)

- **Production** (docker-compose.infrastructure.yml + docker-compose.app.yml):
  - Split compose files (infrastructure vs app)
  - Frontend on port 3000/3001 (Node.js adapter, no HMR)
  - API on port 8000/8001
  - nginx on host (ports 80/443)
  - PostgreSQL + pgvector required
  - Static assets served by nginx (NOT container)

**Health Checks:**
- API: `/api/health`, `/api/health/db`, `/api/health/redis`
- Frontend: `wget http://127.0.0.1:3000` (homepage)
- Deployment blocks on failed health checks (automatic rollback)

**Rollback Procedure:**
- Automatic: Health checks fail → deployment aborts, keeps old environment
- Manual: Switch nginx config back, reload nginx, restart old containers

**Monitoring:**
- nginx logs: `/var/log/nginx/boardofone-{blue|green}-{access|error}.log`
- Container logs: `docker logs {project}-{service}-1`
- Static assets: `access_log off` (performance optimization)

---

## Common Patterns

### Persona Prompt Composition

```python
from bo1.prompts.reusable_prompts import compose_persona_prompt

# Compose: BESPOKE + DYNAMIC + GENERIC
system_prompt = compose_persona_prompt(
    persona_system_role=persona["system_prompt"],  # From personas.json
    problem_statement="Should we invest $500K...",
    participant_list="Maria, Zara, Tariq",
    current_phase="discussion"
)
```

### Parallel Expert Calls (Initial Round)

```python
# All personas contribute simultaneously
contributions = await asyncio.gather(
    *[call_persona(code) for code in persona_codes]
)
```

### Graph Execution with Checkpointing

```python
from bo1.graph.config import create_deliberation_graph
from bo1.graph.state import create_initial_state

# Create graph with Redis checkpointing
graph = create_deliberation_graph()  # Auto-creates RedisSaver from env

# Create initial state
state = create_initial_state(
    session_id="session-123",
    problem=problem,
    personas=personas,
    max_rounds=10
)

# Execute with checkpointing
config = {"configurable": {"thread_id": "session-123"}}
result = await graph.ainvoke(state, config=config)

# Resume from checkpoint
result = await graph.ainvoke(None, config=config)  # Continues from last checkpoint
```

### Pause/Resume Sessions

```python
from bo1.interfaces.console import run_console_deliberation

# Start new deliberation - session ID is automatically generated
result = await run_console_deliberation(problem)
session_id = result["session_id"]

# Resume from checkpoint later
result = await run_console_deliberation(problem, session_id=session_id)

# Console will display:
# - Current round, phase, experts
# - Cost so far
# - Prompt: "Continue deliberation? (y/n)"
```

**Checkpoint TTL**: 7 days (configurable via `CHECKPOINT_TTL_SECONDS` env var)

### State Conversion (v1 ↔ LangGraph)

```python
from bo1.graph.state import state_to_v1, v1_to_state

# LangGraph state → v1 Pydantic models (for agent calls)
v1_state = state_to_v1(graph_state)
result = await some_agent.run(v1_state)

# v1 Pydantic → LangGraph state (for graph updates)
graph_state = v1_to_state(v1_state)
```

### Cost Analytics

```python
from bo1.graph.analytics import (
    calculate_cost_breakdown,
    export_phase_metrics_csv,
    get_most_expensive_phases,
)

# Get phase cost breakdown
breakdown = calculate_cost_breakdown(state)
for item in breakdown:
    print(f"{item['phase']}: ${item['cost']:.4f} ({item['percentage']:.1f}%)")

# Export to CSV for analysis
export_phase_metrics_csv(state, "exports/session_costs.csv")

# Find most expensive phases
top_3 = get_most_expensive_phases(state, top_n=3)
```

### Database Connection Pooling

```python
from bo1.state.postgres_manager import db_session

# CORRECT: Use db_session() context manager (auto-pooling + cleanup)
with db_session() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user_context WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        # Auto-commits on success, auto-rolls back on error

# DEPRECATED: Never use get_connection() - removed in 2025-01-23 refactor
# conn = get_connection()  # ❌ Don't do this - connection pool exhaustion!
```

**Database Connection Best Practices**:
- Always use `db_session()` context manager (automatic pooling)
- Never manually call `conn.commit()` or `conn.close()` (handled automatically)
- Connection pool: ThreadedConnectionPool (min=1, max=20)
- All PostgreSQL functions in `postgres_manager.py` use pooling (2025-01-23 refactor)

---

## Testing Strategy

1. **Unit**: Pydantic models, prompt composition, recommendation aggregation
   - `make test-unit` or `pytest -m unit` - Fast tests, no API calls
2. **Integration**: Redis persistence, LLM calls, convergence detection, LangGraph execution
   - `make test-integration` or `pytest -m integration` - Requires Redis + PostgreSQL + API keys
   - `pytest -m "not requires_llm"` - Skip LLM tests (faster CI/local checks)
3. **Graph Tests**: LangGraph node execution, routing, checkpointing
   - `pytest tests/graph/ -v` - Tests for nodes, routers, loop prevention
4. **Demo**: Full pipeline validation (Weeks 1-5)
   - `make demo` - Runs complete deliberation with real LLM calls

**Running Specific Tests**:
```bash
# Run single test file
pytest tests/graph/test_loop_prevention.py -v

# Run single test function
pytest tests/graph/test_loop_prevention.py::test_check_convergence_with_high_score -v

# Run tests with coverage report
make test-coverage  # Generates htmlcov/index.html
```

**Pre-Push Checklist**:
1. `make pre-commit` - Ensures code quality (lint + format + typecheck)
2. `pytest -m "not requires_llm"` - Fast test suite (no API costs)
3. Optionally: `make test` - Full test suite including LLM calls

---

## What NOT to Do

**Code & Architecture:**
- Don't create new personas (use existing 45 from `personas.json`)
- Don't use binary voting (use recommendation system with `<recommendation>` tag)
- Don't use `VoteDecision` enum (removed - use free-form recommendation strings)
- Don't hardcode prompts (use composition functions)
- Don't ignore cost optimization (prompt caching is critical)
- Don't let context grow quadratically (use hierarchical summarization)
- Don't modify `check_convergence_node()` without handling `None` values for `convergence_score`
- Don't call functions `collect_votes()` or `aggregate_votes_ai()` (use `collect_recommendations()` and `aggregate_recommendations_ai()`)

**Frontend Environment Variables:**
- Don't use `import.meta.env.PUBLIC_API_URL` (use `$env/dynamic/public` for runtime resolution)
- Don't set `envPrefix` in `adapter()` config (causes conflicts with runtime env vars)
- Don't use `VITE_API_BASE_URL` (deprecated - use `PUBLIC_API_URL`)

**nginx Configuration:**
- Don't use `limit_conn off;` (invalid syntax - use high number like `limit_conn conn_limit 100;`)
- Don't proxy static assets through Node.js (serve directly from `/var/www/boardofone/static-*`)
- Don't apply connection limits to static asset locations (HTTP/2 parallel loading needs 100+ connections)

**Docker & Deployment:**
- Don't use `localhost` for inter-container communication (use Docker service names: `postgres`, `redis`, `supertokens`)
- Don't modify nginx configs on server directly (update in repo, deploy via GitHub Actions)
- Don't skip static asset extraction step during deployment (causes 503 errors)
- Don't restart containers during active user sessions (use blue-green deployment)

---

## Production Troubleshooting

**Issue: Frontend shows 502 Bad Gateway**
- Check: `docker logs boardofone-frontend-1` or `boardofone-green-frontend-1`
- Common cause: Frontend container crash-looping
- Solution: Check for env var conflicts, missing `PUBLIC_API_URL`, or build errors

**Issue: Static assets return 503 errors**
- Check: `/var/log/nginx/boardofone-*-error.log` for "limiting connections"
- Common cause: Connection limit too low for HTTP/2 parallel loading
- Solution: Ensure `limit_conn conn_limit 100;` in static asset location blocks

**Issue: Static assets return HTML instead of JS (MIME type error)**
- Check: `curl -I https://boardof.one/_app/immutable/chunks/*.js` → should be `application/javascript`
- Common cause: nginx location blocks not matching, or static files not extracted
- Solution: Verify `/var/www/boardofone/static-{env}/_app/` exists and has files

**Issue: "localhost:8000" appears in production browser console**
- Common cause: Using `import.meta.env.PUBLIC_API_URL` (build-time) instead of `$env/dynamic/public` (runtime)
- Solution: Update all frontend files to use `import { env } from '$env/dynamic/public'`

**Issue: Docker containers can't connect to postgres/redis**
- Check: Container logs show "connection refused localhost:5432"
- Common cause: Using `localhost` instead of Docker service names
- Solution: Use `postgres:5432`, `redis:6379` in connection strings (NOT `localhost`)

**Issue: SuperTokens cookies rejected "invalid domain"**
- Check: Browser console shows cookie domain mismatch
- Common cause: `COOKIE_DOMAIN` env var mismatch or missing
- Solution: Set `COOKIE_DOMAIN=boardof.one` and `COOKIE_SECURE=true` in production `.env`

**Issue: Google OAuth sign-in fails with "redirect_uri_mismatch"**
- Check: Google Cloud Console → OAuth 2.0 Client → Authorized redirect URIs
- Common cause: Missing or incorrect redirect URI for production domain
- Solution: Add `https://boardof.one/callback` to authorized redirect URIs in Google Cloud Console
- Note: Production uses different OAuth client ID than dev

**Issue: OAuth succeeds but session not persisting (401 on /api/auth/me)**
- Check: Browser console for cookie rejection warnings
- Common cause: Missing `COOKIE_SECURE=true` or `COOKIE_DOMAIN=boardof.one`
- Solution: Verify all SuperTokens env vars are set correctly:
  ```bash
  SUPERTOKENS_API_DOMAIN=https://boardof.one
  SUPERTOKENS_WEBSITE_DOMAIN=https://boardof.one
  COOKIE_SECURE=true
  COOKIE_DOMAIN=boardof.one
  ```

**Issue: OAuth sign-in fails with "Email not whitelisted"**
- Check: API logs show "Sign-in attempt rejected: {email} not whitelisted"
- Common cause: `BETA_WHITELIST` env var missing or email not in list
- Solution: Add email to `BETA_WHITELIST` in production `.env` (comma-separated)

**Issue: OAuth configuration not loading (missing client ID/secret)**
- Check: API logs show "Google OAuth enabled but credentials missing"
- Common cause: `GOOGLE_OAUTH_CLIENT_ID` or `GOOGLE_OAUTH_CLIENT_SECRET` not passed to container
- Solution: Verify env vars exist in `.env` and are listed in `docker-compose.app.yml`

**Deployment Debugging:**
```bash
# SSH into server
ssh root@139.59.201.65

# Check which environment is active
curl -sI https://boardof.one | grep X-Environment

# View nginx error logs
tail -100 /var/log/nginx/boardofone-*-error.log

# Check container status
docker ps --format 'table {{.Names}}\t{{.Status}}'

# View container logs
docker logs boardofone-frontend-1 --tail 50
docker logs boardofone-api-1 --tail 50

# Check static assets
ls -la /var/www/boardofone/static-blue/_app/immutable/
ls -la /var/www/boardofone/static-green/_app/immutable/

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```
