# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project: Board of One (bo1)

Console-based AI system using multi-agent deliberation (Claude personas) to solve complex problems through structured debate and synthesis.

**Status**: v2 deployed to production (https://boardof.one)

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
make up              # Start all services (Redis + PostgreSQL + API + Supabase Auth + app)

# Development
make run             # Run deliberation (interactive)
make demo            # Run full pipeline demo
make shell           # Bash in container
make logs            # View all container logs
make logs-app        # View app logs only

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

# API (Web Interface)
# API runs automatically with `make up` on http://localhost:8000
# Access admin docs: http://localhost:8000/admin/docs (requires admin auth)
# Supabase Auth: http://localhost:9999

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
- `bo1/interfaces/console.py` - Console adapter with pause/resume support
- `backend/api/main.py` - FastAPI application entry point
- `backend/api/streaming.py` - SSE streaming endpoints for real-time updates
- `backend/api/middleware/auth.py` - Supabase JWT authentication middleware
- `backend/api/admin.py` - Admin-only endpoints (session monitoring, metrics)
- `docker-compose.prod.yml` - Production deployment configuration
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
- FastAPI with SSE streaming (`backend/api/`)
- Supabase GoTrue auth (JWT-based, OAuth support for Google/GitHub/LinkedIn)
- Admin-only API docs (`/admin/docs` requires X-Admin-Key or admin JWT)
- Public landing page at root (`/`)
- Endpoints: health, sessions, streaming, context, control, admin
- Production compose file: `docker-compose.prod.yml`

**Cost targets**:
- $0.10-0.15 per sub-problem deliberation
- 5-15 min per deliberation
- 60-70% cost reduction via prompt caching

**User sovereignty**:
- System provides recommendations, NOT directives
- "We recommend X" not "You must do X"

**Safety**:
- All personas refuse harmful/illegal/unethical requests
- Generic safety protocol in `reusable_prompts.py`

**Production Deployment** (Blue-Green):
- Automated via GitHub Actions workflow
- Zero-downtime blue-green deployment
- Automated Let's Encrypt SSL certificate management
- Health checks before traffic switch
- Automatic rollback on failure
- Docker network hostnames for inter-container communication:
  - DATABASE_URL uses `postgres` hostname (not `localhost`)
  - REDIS_URL uses `redis` hostname (not `localhost`)
  - Supabase auth uses `postgres` hostname for DATABASE_URL
- Infrastructure components (postgres, redis, supabase-auth) shared between blue/green
- Application containers (api, frontend) deployed to separate blue/green environments

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

- Don't create new personas (use existing 45 from `personas.json`)
- Don't use binary voting (use recommendation system with `<recommendation>` tag)
- Don't use `VoteDecision` enum (removed - use free-form recommendation strings)
- Don't hardcode prompts (use composition functions)
- Don't ignore cost optimization (prompt caching is critical)
- Don't let context grow quadratically (use hierarchical summarization)
- Don't modify `check_convergence_node()` without handling `None` values for `convergence_score`
- Don't call functions `collect_votes()` or `aggregate_votes_ai()` (use `collect_recommendations()` and `aggregate_recommendations_ai()`)
