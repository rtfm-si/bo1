# Board of One - MVP Implementation Roadmap

**Timeline**: 14.5 weeks (101 days)
**Current Status**: Week 3.5 Complete (Database & Infrastructure Ready)
**Next Phase**: Week 4 - LangGraph Migration Part 1 (Days 22-28)
**Target Launch**: Week 14 Day 101 (Public Beta / MVP)

---

## Executive Summary

This roadmap covers the complete path from Week 3 completion to **10/10 production-grade MVP launch**, integrating:
- **Week 3.5**: Database & infrastructure setup (PostgreSQL, Alembic, environment config)
- **Weeks 4-5**: Console → LangGraph migration (unified architecture) + **developer onboarding tools**
- **Weeks 6-7**: Web API adapter (FastAPI + SSE streaming) + Supabase Auth
- **Week 8**: Stripe payments + rate limiting + GDPR user rights
- **Week 9**: Production hardening + **vendor outage contingency + cost anomaly detection + feature flags + SLI/SLO/SLA**
- **Weeks 10-11**: Admin dashboard (monitoring, analytics, kill switches, ntfy.sh alerts)
- **Week 12**: Resend integration + email templates
- **Week 13**: Final QA, security audit, load testing + **blue-green deployment**
- **Week 14**: Launch preparation + user documentation + **business continuity planning**

**Key Decisions**:
- ✅ **Unified LangGraph architecture** (console + web, NOT dual systems)
- ✅ **DigitalOcean deployment** (NOT Render, Railway, or Fly.io)
- ✅ **Resend for emails** (transactional, developer-friendly)
- ✅ **ntfy.sh for admin alerts** (runaway sessions, cost reports)
- ✅ **100% confidence infinite loop prevention** (5-layer safety system)
- ✅ **10/10 Production Excellence** (vendor resilience, cost controls, zero-downtime deploys, business continuity)

---

## Progress Tracking

| Week | Phase | Status | Tasks Complete |
|------|-------|--------|----------------|
| 1-3 | Console v1 Foundation | ✅ Complete | 228/228 (100%) |
| 3.5 | Database & Infrastructure Setup | ✅ Complete | 35/35 (100%) |
| 4-5 | LangGraph Migration | 🔄 In Progress | 56/134 (42%) |
| 6-7 | Web API Adapter + Auth | 📅 Planned | 0/112 (0%) |
| 8 | Payments + Rate Limiting + GDPR | 📅 Planned | 0/98 (0%) |
| 9 | Production Hardening | 📅 Planned | 0/210 (0%) |
| 10-11 | Admin Dashboard | 📅 Planned | 0/98 (0%) |
| 12 | Resend Integration | 📅 Planned | 0/42 (0%) |
| 13 | QA + Security Audit + Deployment | 📅 Planned | 0/167 (0%) |
| 14 | Launch + Documentation | 📅 Planned | 0/112 (0%) |
| **Total** | | | **319/1236 (26%)** |

---

## Week 3.5 (Day 21): Database & Infrastructure Setup

**Goal**: Establish database schema, migrations, and environment configuration before LangGraph work begins

**Status**: 0/35 tasks complete

### Day 21: Database Setup & Environment Configuration

**Tasks**:
- [ ] Install PostgreSQL 15+ with pgvector extension
- [ ] Setup Alembic for database migrations
  ```bash
  uv add alembic psycopg2-binary
  alembic init migrations
  ```
- [ ] Create initial schema migration (`migrations/versions/001_initial_schema.py`)
  - [ ] users table (id, email, auth_provider, subscription_tier, created_at, gdpr_consent_at)
  - [ ] sessions table (id, user_id, problem_statement, status, total_cost, created_at)
  - [ ] contributions table (id, session_id, persona_code, content, round_number)
  - [ ] votes table (id, session_id, persona_code, vote_choice, reasoning)
  - [ ] personas table (id, code, name, expertise, system_prompt)
  - [ ] audit_log table (id, user_id, action, resource_type, resource_id, timestamp)
- [ ] Create RLS policies for multi-tenancy
  ```sql
  ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
  CREATE POLICY user_sessions ON sessions FOR ALL USING (auth.uid() = user_id);
  ```
- [ ] Create indexes for performance
  ```sql
  CREATE INDEX idx_sessions_user_id ON sessions(user_id);
  CREATE INDEX idx_sessions_status ON sessions(status);
  CREATE INDEX idx_contributions_session_id ON contributions(session_id);
  ```
- [ ] Seed personas data (45 experts from bo1/data/personas.json)
- [ ] Create environment configuration
  - [ ] Create .env.example with all required variables
  - [ ] Document each environment variable (README or docs/)
  - [ ] Setup secrets management (Doppler, AWS Secrets Manager, or 1Password)
  - [ ] Create .env for development
  - [ ] Create .env.staging for staging
  - [ ] Create .env.production template
- [ ] Document Redis key patterns and TTL strategy
  - [ ] session:{id} (TTL: 7 days)
  - [ ] checkpoint:{session_id}:{step} (TTL: 7 days)
  - [ ] ratelimit:{user_id}:{action} (TTL: 1 minute)
  - [ ] cache:{key} (TTL: 30 days)
- [ ] Create Redis cleanup job for expired data

**Validation**:
- [ ] Alembic migrations run successfully: `alembic upgrade head`
- [ ] Can downgrade: `alembic downgrade -1`
- [ ] Database schema matches design (15 tables)
- [ ] RLS policies enforce user isolation
- [ ] Personas seeded (45 rows in personas table)
- [ ] .env.example contains all 25+ required variables
- [ ] Redis key patterns documented

**Tests**:
```bash
# Test migrations
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Test database connection
pytest tests/test_database_setup.py -v

# Verify RLS policies
pytest tests/test_row_level_security.py -v

# Test environment loading
pytest tests/test_environment_config.py -v
```

**Deliverables**:
- migrations/versions/001_initial_schema.py
- .env.example
- docs/DATABASE_SCHEMA.md
- docs/REDIS_KEY_PATTERNS.md
- docs/ENVIRONMENT_VARIABLES.md

---

## Week 4 (Days 22-28): LangGraph Console Migration - Part 1

**Goal**: Begin migrating console to LangGraph architecture with safety guarantees

**Status**: 56/56 tasks complete (100%) ✅

### Day 22: LangGraph Setup & Training

**Value**: Team understanding and environment ready for migration

#### Training & Research

- [x] Complete LangGraph official tutorial (2-3 hours)
  - [x] Read: https://langchain-ai.github.io/langgraph/tutorials/introduction/
  - [x] Understand: StateGraph, nodes, edges, checkpoints
  - [x] Study: Human-in-the-loop patterns
  - [x] Review: Infinite loop prevention (recursion limits)
- [x] Study LangGraph architecture patterns
  - [x] Conditional routing examples
  - [x] Checkpoint recovery patterns
  - [x] Streaming implementations (SSE + WebSocket)
  - [x] Error handling in graphs

#### Environment Setup

- [x] Install LangGraph dependencies
  ```bash
  uv add langgraph langgraph-checkpoint-redis
  ```
- [x] Create graph module structure
  ```bash
  mkdir -p bo1/graph
  touch bo1/graph/__init__.py
  touch bo1/graph/state.py
  touch bo1/graph/nodes.py
  touch bo1/graph/config.py
  touch bo1/graph/execution.py
  touch bo1/graph/routers.py
  ```
- [x] Create safety module structure
  ```bash
  mkdir -p bo1/graph/safety
  touch bo1/graph/safety/__init__.py
  touch bo1/graph/safety/loop_prevention.py
  touch bo1/graph/safety/kill_switches.py
  ```

#### Hello World Graph

- [x] Create simple "hello world" graph
  - [x] Define basic state schema (TypedDict with 2 fields)
  - [x] Create 2 nodes (node1, node2)
  - [x] Connect with edge (node1 → node2)
  - [x] Compile graph without checkpointer
  - [x] Execute with `.invoke()`
  - [x] Verify output
- [x] Test with checkpointer
  - [x] Add MemorySaver checkpointer
  - [x] Execute with thread_id
  - [x] Verify checkpoint created
  - [x] Load state from checkpoint

#### Pre-commit Hooks Setup
- [x] Install pre-commit framework: `uv add --dev pre-commit`
- [x] Create .pre-commit-config.yaml
  ```yaml
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.1.8
      hooks:
        - id: ruff
        - id: ruff-format
    - repo: https://github.com/pre-commit/mirrors-mypy
      rev: v1.7.1
      hooks:
        - id: mypy
  ```
- [x] Install hooks: `pre-commit install`
- [x] Test: Make a bad commit (should be blocked)

**Validation**:
- [x] LangGraph installed successfully (`python -c "import langgraph"`)
- [x] Can run basic graph (`python examples/hello_world_graph.py`)
- [x] Team understands graph/node/edge concepts
- [x] Checkpoint persistence works (MemorySaver)
- [x] Pre-commit runs on every commit
- [x] Bad code is rejected (test with intentional lint error)

**Tests**:
```bash
pytest tests/test_graph_setup.py -v
```

**Deliverables**:
- bo1/graph/ module structure
- examples/hello_world_graph.py
- .pre-commit-config.yaml
- docs/LANGGRAPH_TRAINING.md

#### One-Command Developer Setup

**Value**: New developers can start contributing in <5 minutes

**Tasks**:
- [x] Create `make setup-dev` command
  ```makefile
  setup-dev: ## One-command setup for new developers
  	@echo "Setting up Board of One development environment..."
  	@command -v uv >/dev/null || pip install uv
  	@uv sync --frozen
  	@cp .env.example .env
  	@echo "Installing pre-commit hooks..."
  	@pre-commit install
  	@echo "Starting Docker services..."
  	@make up
  	@sleep 5
  	@echo "Running database migrations..."
  	@make migrate
  	@echo "Seeding personas..."
  	@python scripts/seed_personas.py
  	@echo "✅ Setup complete! Run 'make run' to start."
  ```
- [x] Test on fresh machine (delete .env, remove containers, run setup)
- [x] Time the setup (should be <5 minutes)

**Validation**:
- [x] New developer can run `make setup-dev` and be ready in <5 minutes
- [x] Setup script handles missing dependencies gracefully

**Deliverables**:
- Updated Makefile with setup-dev target

#### Code Review Guidelines

**Value**: Consistent code quality standards

**Tasks**:
- [x] Create docs/CODE_REVIEW_GUIDELINES.md
  ```markdown
  # Code Review Guidelines

  ## What to Look For

  ### Security
  - [ ] No hardcoded secrets (API keys, passwords)
  - [ ] User input validated (Pydantic models)
  - [ ] SQL queries parameterized (no string interpolation)
  - [ ] Auth required on protected endpoints

  ### Testing
  - [ ] New code has tests
  - [ ] Tests cover happy path + edge cases
  - [ ] Tests are deterministic (no flaky tests)

  ### Performance
  - [ ] No N+1 queries (use joins or batch loading)
  - [ ] Expensive operations cached (Redis)
  - [ ] Database queries use indexes

  ### Code Quality
  - [ ] Code is readable (clear variable names)
  - [ ] Functions are small (<50 lines)
  - [ ] No duplication (DRY principle)
  - [ ] Type hints present (mypy passes)

  ### Documentation
  - [ ] Complex logic explained (comments or docstrings)
  - [ ] Public APIs documented (FastAPI auto-docs)
  - [ ] Breaking changes noted in PR description

  ## PR Template

  Use this template for all PRs:

  ```
  ## Summary
  [Brief description of changes]

  ## Changes
  - [List of changes]

  ## Testing
  - [ ] Unit tests added/updated
  - [ ] Manual testing completed
  - [ ] Pre-commit checks pass

  ## Screenshots (if UI changes)
  [Add screenshots]

  ## Breaking Changes
  [List any breaking changes, or "None"]
  ```
  ```
- [x] Add PR template: .github/pull_request_template.md

**Validation**:
- [x] CODE_REVIEW_GUIDELINES.md created and reviewed
- [x] PR template available in GitHub

**Deliverables**:
- docs/CODE_REVIEW_GUIDELINES.md
- .github/pull_request_template.md

---

### Day 23: Define Graph State Schema

**Value**: Type-safe state management for LangGraph

#### Graph State Model

- [x] Create `bo1/graph/state.py`
  - [x] Define `DeliberationGraphState` (TypedDict)
    - [x] session_id: str
    - [x] problem: Problem
    - [x] current_sub_problem: SubProblem | None
    - [x] personas: list[PersonaProfile]
    - [x] contributions: list[ContributionMessage]
    - [x] round_summaries: list[str]
    - [x] phase: DeliberationPhase
    - [x] round_number: int
    - [x] max_rounds: int
    - [x] metrics: DeliberationMetrics
    - [x] facilitator_decision: FacilitatorDecision | None
    - [x] should_stop: bool
    - [x] stop_reason: str | None
    - [x] user_input: str | None (for human-in-loop)
    - [x] current_node: str (for visualization)
  - [x] Add helper functions
    - [x] `create_initial_state()` - Initialize from Problem
    - [x] `validate_state()` - Pydantic-style validation
    - [x] `state_to_dict()` - Serialize for checkpointing

#### Compatibility Bridge

- [x] Create conversion functions (v1 ↔ v2)
  - [x] `deliberation_state_to_graph_state()`
    - [x] Map v1 DeliberationState → v2 DeliberationGraphState
    - [x] Preserve all existing fields
    - [x] Add default values for new fields
  - [x] `graph_state_to_deliberation_state()`
    - [x] Map v2 → v1 (for agent calls during migration)
    - [x] Validate all required fields present
  - [x] Document field mappings (docstrings)

#### Testing

- [x] Test: Create DeliberationGraphState from Problem
- [x] Test: Validate state schema (all required fields)
- [x] Test: Convert v1 → v2 (existing DeliberationState)
- [x] Test: Convert v2 → v1 (graph state → agent input)
- [x] Test: Round-trip conversion (v1 → v2 → v1, no data loss)

**Validation**:
- [x] DeliberationGraphState defined with all fields
- [x] Conversion functions work bidirectionally
- [x] No data loss in round-trip conversion
- [x] Pydantic validation catches invalid states

**Tests**:
```bash
pytest tests/test_graph_state.py -v
```

**Deliverables**:
- bo1/graph/state.py
- Conversion functions (v1 ↔ v2)

#### Development Troubleshooting Guide

**Value**: Reduce developer onboarding friction

**Tasks**:
- [x] Create docs/TROUBLESHOOTING.md with common errors
  ```markdown
  # Development Troubleshooting Guide

  ## Common Errors

  ### Error: "Redis connection refused"
  **Symptom**: `ConnectionRefusedError: [Errno 61] Connection refused`
  **Cause**: Redis not running
  **Fix**: `make up` (starts Redis container)

  ### Error: "Database does not exist"
  **Symptom**: `psycopg2.OperationalError: database "boardofone" does not exist`
  **Cause**: Database not created
  **Fix**: `alembic upgrade head`

  ### Error: "ANTHROPIC_API_KEY not set"
  **Symptom**: `KeyError: 'ANTHROPIC_API_KEY'`
  **Cause**: Missing .env file
  **Fix**: `cp .env.example .env` and add your API key

  ### Error: "Persona not found"
  **Symptom**: `PersonaNotFoundError: Persona 'maria' not found`
  **Cause**: Personas not seeded
  **Fix**: `python scripts/seed_personas.py`

  ### Error: Tests fail with "No module named 'bo1'"
  **Symptom**: `ModuleNotFoundError: No module named 'bo1'`
  **Cause**: Wrong directory or missing uv sync
  **Fix**: `cd /Users/si/projects/bo1 && uv sync`

  ### Error: Pre-commit hook fails
  **Symptom**: `ruff....Failed`
  **Cause**: Code doesn't pass linting
  **Fix**: `make fix` (auto-fix) or manually fix lint errors

  ## Performance Issues

  ### Issue: Deliberation very slow locally
  **Cause**: Using Sonnet 4.5 (expensive) instead of Haiku (fast)
  **Fix**: Set `LLM_MODEL=claude-haiku-4.5` in .env for local dev

  ### Issue: Tests take forever
  **Cause**: Running LLM tests
  **Fix**: `pytest -m "not requires_llm"` (skip LLM tests)
  ```
- [x] Add FAQ section for development
- [x] Link from main README.md

**Validation**:
- [x] TROUBLESHOOTING.md covers 10+ common errors
- [x] Linked from README.md

**Deliverables**:
- docs/TROUBLESHOOTING.md

---

### Day 24: Infinite Loop Prevention - Layer 1-3

**Value**: 100% confidence that graphs cannot loop indefinitely

#### Layer 1: Recursion Limit (LangGraph Built-in)

- [x] Create `bo1/graph/safety/loop_prevention.py`
  - [x] Define `DELIBERATION_RECURSION_LIMIT = 55`
    - [x] Calculation: 15 max rounds × 3 nodes/round + 10 overhead
    - [x] Document: Why 55 is safe upper bound
  - [x] Add to graph compilation
    - [x] `graph.compile(recursion_limit=DELIBERATION_RECURSION_LIMIT)`
  - [x] Test: Verify GraphRecursionError raised at limit

#### Layer 2: Cycle Detection (Graph Validation)

- [x] Implement `validate_graph_acyclic()`
  - [x] Convert LangGraph to NetworkX DiGraph
  - [x] Use `nx.simple_cycles()` to find cycles
  - [x] For each cycle: Check for conditional exit
  - [x] Raise `ValueError` if uncontrolled cycle found
  - [x] Document: What makes a cycle "safe"
- [x] Create `has_exit_condition()`
  - [x] Check if cycle has conditional edge leading OUT
  - [x] Verify at least one path breaks the loop
  - [x] Return True if safe, False if dangerous

#### Layer 3: Round Counter (Domain Logic)

- [x] Create `check_convergence_node()`
  - [x] Check: `round_number >= max_rounds` → set `should_stop = True`
  - [x] Check: `round_number >= 15` → absolute hard cap
  - [x] Calculate convergence metrics (semantic similarity)
  - [x] Set `stop_reason` (max_rounds, hard_cap, consensus)
  - [x] Return updated state
- [x] Create `route_convergence_check()`
  - [x] If `should_stop == True` → return "vote"
  - [x] Else → return "facilitator_decide" (continue loop)
  - [x] Guarantee: Round counter increments monotonically (no reset)

#### Testing

- [x] Test: Recursion limit (create infinite loop, verify error)
- [x] Test: Cycle detection (uncontrolled cycle raises ValueError)
- [x] Test: Round counter enforces max_rounds
- [x] Test: Absolute hard cap (15 rounds) triggers
- [x] Test: Conditional routing respects should_stop flag

**Validation**:
- [x] GraphRecursionError raised after 55 steps
- [x] Cycle validation catches unsafe loops at compile time
- [x] Round counter prevents deliberations >15 rounds
- [x] All tests pass (100% confidence in loop prevention)

**Tests**:
```bash
pytest tests/test_loop_prevention.py -v
pytest tests/test_cycle_detection.py -v
```

---

### Day 25: Infinite Loop Prevention - Layer 4-5

**Value**: Additional safety layers (timeout, cost guards)

#### Layer 4: Timeout Watchdog

- [x] Create `execute_deliberation_with_timeout()`
  - [x] Wrap `graph.ainvoke()` with `asyncio.wait_for()`
  - [x] Default timeout: 3600 seconds (1 hour)
  - [x] On timeout:
    - [x] Log error with session details
    - [x] Load last checkpoint (state preserved)
    - [x] Mark session as timed out (metadata)
    - [x] Raise TimeoutError (catchable)
  - [x] Document: When timeouts indicate problems

#### Layer 5: Cost-Based Kill Switch

- [x] Create `cost_guard_node()`
  - [x] Check: `total_cost >= MAX_COST_PER_SESSION` ($1.00 default)
  - [x] If over budget:
    - [x] Set `should_stop = True`
    - [x] Set `stop_reason = "cost_budget_exceeded"`
    - [x] Log warning with current cost
  - [x] Return updated state
- [x] Add to graph BEFORE expensive nodes
  - [x] Insert between facilitator and persona nodes
  - [x] Conditional routing: budget exceeded → force synthesis
- [x] Make configurable
  - [x] Environment variable: `MAX_COST_PER_SESSION`
  - [x] Per-tier limits (free, pro, enterprise)

#### Multi-Layer Testing

- [x] Test: Timeout kills long-running session
  - [x] Create slow node (`await asyncio.sleep(10)`)
  - [x] Execute with 1-second timeout
  - [x] Verify TimeoutError raised
  - [x] Verify checkpoint preserved
- [x] Test: Cost guard stops expensive session
  - [x] Mock LLM responses with high costs
  - [x] Trigger cost guard ($1.01 total)
  - [x] Verify early termination
  - [x] Verify synthesis still runs
- [x] Test: All 5 layers work independently
  - [x] Test each layer in isolation
  - [x] Test combined (multiple layers triggered)
  - [x] Verify 100% confidence in prevention

#### Documentation

- [x] Document 5-layer system in `LOOP_PREVENTION.md`
  - [x] Layer 1: Recursion limit (how it works, why 55)
  - [x] Layer 2: Cycle detection (compile-time validation)
  - [x] Layer 3: Round counter (domain logic, max 15)
  - [x] Layer 4: Timeout watchdog (1 hour hard limit)
  - [x] Layer 5: Cost kill switch ($1 budget cap)
  - [x] Combined guarantee: 100% confidence
- [x] Add to CLAUDE.md
  - [x] Reference loop prevention in architecture section
  - [x] Link to LOOP_PREVENTION.md

**Validation**:
- [x] Timeout works (long sessions killed)
- [x] Cost guard works (expensive sessions stopped)
- [x] All 5 layers tested independently
- [x] Documentation complete and accurate

**Tests**:
```bash
pytest tests/test_timeout_watchdog.py -v
pytest tests/test_cost_guard.py -v
pytest tests/test_multi_layer_prevention.py -v
```

---

### Day 26: Kill Switches (User + Admin)

**Value**: Users control their sessions, admins can intervene

#### Session Manager

- [x] Create `bo1/graph/execution.py`
  - [x] `SessionManager` class
    - [x] `active_executions: dict[str, asyncio.Task]`
    - [x] `start_session()` - Create background task
    - [x] `kill_session()` - User kills own session
    - [x] `admin_kill_session()` - Admin kills any session
    - [x] `admin_kill_all_sessions()` - Emergency shutdown
    - [x] `is_admin()` - Check admin role
  - [x] Ownership tracking
    - [x] Store `user_id` in session metadata (Redis)
    - [x] Verify ownership before kill (PermissionError if mismatch)

#### User Kill Switch

- [x] Implement `kill_session()`
  - [x] Check ownership (user can ONLY kill own sessions)
  - [x] Cancel background task (`task.cancel()`)
  - [x] Update metadata (`status = "killed"`, `killed_at`, `killed_by`, `kill_reason`)
  - [x] Preserve checkpoint (for post-mortem inspection)
  - [x] Log termination (audit trail)
  - [x] Return success/failure boolean
- [ ] API endpoint (console mode for now)
  - [ ] `/api/admin/sessions/{session_id}/kill` (POST)
  - [ ] Validate user owns session
  - [ ] Call SessionManager.kill_session()
  - [ ] Return status

#### Admin Kill Switch

- [x] Implement `admin_kill_session()`
  - [x] NO ownership check (admins can kill any session)
  - [x] Verify admin role (`is_admin()` check)
  - [x] Cancel task, update metadata (same as user kill)
  - [x] Log with admin user ID
  - [x] Raise PermissionError if not admin
- [x] Implement `admin_kill_all_sessions()`
  - [x] Emergency use only (system maintenance, runaway costs)
  - [x] Iterate all active sessions (`redis.list_sessions()`)
  - [x] Kill each with admin_kill_session()
  - [x] Return count of killed sessions
  - [x] Log WARNING (critical action)

#### Graceful Shutdown

- [x] Signal handlers for deployment
  - [x] Register `SIGTERM` handler
  - [x] Register `SIGINT` handler (Ctrl+C)
  - [x] On signal:
    - [x] Get all active sessions
    - [x] Cancel tasks with 5-second grace period
    - [x] Save checkpoints before exit
    - [x] Log shutdown event

#### Testing

- [x] Test: User can kill own session
  - [x] Start session, verify running
  - [x] Call kill_session() with same user_id
  - [x] Verify task canceled, metadata updated
- [x] Test: User CANNOT kill other users' sessions
  - [x] Start session (user_1)
  - [x] Attempt kill (user_2)
  - [x] Verify PermissionError raised
- [x] Test: Admin can kill any session
  - [x] Start session (user_1)
  - [x] Admin kills session
  - [x] Verify success
- [x] Test: Admin can kill all sessions
  - [x] Start 3 sessions (different users)
  - [x] Admin kills all
  - [x] Verify all killed, count correct
- [x] Test: Graceful shutdown preserves checkpoints
  - [x] Start session, send SIGTERM
  - [x] Verify checkpoint saved before exit

**Validation**:
- [x] User kill switch works (ownership enforced)
- [x] Admin kill switch works (no ownership check)
- [x] Admin kill all works (emergency use)
- [x] Graceful shutdown preserves state
- [x] Audit trail logged for all kills

**Tests**:
```bash
pytest tests/test_kill_switches.py -v
pytest tests/test_graceful_shutdown.py -v
```

---

### Day 27: Basic Graph Implementation

**Value**: Simple linear graph works end-to-end

#### Node Implementation

- [x] Create `bo1/graph/nodes.py`
  - [x] `decompose_node()` - Wraps DecomposerAgent
    - [x] Convert graph state → DeliberationState
    - [x] Call existing `decomposer.decompose()`
    - [x] Update graph state with sub-problems
    - [x] Track cost in `phase_costs["problem_decomposition"]`
    - [x] Return updated state
  - [x] `select_personas_node()` - Wraps PersonaSelectorAgent
    - [x] Call existing `selector.recommend_personas()`
    - [x] Update graph state with selected personas
    - [x] Track cost
    - [x] Return updated state
  - [x] `initial_round_node()` - Parallel persona calls
    - [x] Reuse existing `DeliberationEngine.run_initial_round()`
    - [x] Update graph state with contributions
    - [x] Track cost per persona
    - [x] Return updated state

#### Router Functions

- [x] Create `bo1/graph/routers.py`
  - [x] `route_phase()` - Determine next phase
    - [x] After decompose → "select_personas"
    - [x] After select → "initial_round"
    - [x] After initial → "facilitator_decide" (Week 5)
  - [x] Simple routing for now (linear path)
  - [x] Document: How routing will evolve (Week 5)

#### Graph Configuration

- [x] Create `bo1/graph/config.py`
  - [x] `create_deliberation_graph()` function
    - [x] Initialize StateGraph with DeliberationGraphState
    - [x] Add nodes (decompose, select, initial_round)
    - [x] Add edges (decompose → select → initial_round)
    - [x] Set entry point (decompose)
    - [x] Compile with recursion_limit=55
    - [x] Return compiled graph
  - [x] Add Redis checkpointer (optional param)
    - [x] `RedisSaver(redis_url=...)`
    - [x] Configure TTL (7 days, longer than v1 for pause/resume)

#### Testing

- [x] Test: Decompose node works
  - [x] Call with initial state
  - [x] Verify sub-problems created
  - [x] Verify cost tracked
- [x] Test: Select personas node works
  - [x] Call with decomposed state
  - [x] Verify personas selected
  - [x] Verify cost tracked
- [x] Test: Initial round node works
  - [x] Call with selected personas
  - [x] Verify contributions created
  - [x] Verify cost tracked
- [x] Test: Full linear graph executes
  - [x] Create graph, invoke with Problem
  - [x] Verify all 3 nodes execute
  - [x] Verify state updated correctly
  - [x] Verify checkpoint created (if checkpointer enabled)

**Validation**:
- [x] All nodes execute without errors
- [x] State updates correctly at each node
- [x] Cost tracking works
- [x] Linear graph completes end-to-end

**Tests**:
```bash
pytest tests/test_graph_nodes.py -v
pytest tests/test_graph_execution.py -v
```

---

### Day 28: Console Adapter + Benchmarking

**Value**: Console UI works with LangGraph backend, performance validated

#### Console Adapter

- [ ] Create `bo1/interfaces/console.py` (new adapter)
  - [ ] `run_console_deliberation()` function
    - [ ] Load or create session (resume support)
    - [ ] Execute graph with console-friendly event handling
    - [ ] Use `Live` display (Rich) for updates
    - [ ] Handle node events:
      - [ ] `on_node_start` → Show progress
      - [ ] `on_node_end` → Display results
    - [ ] Offer pause at checkpoints
    - [ ] Return final state
  - [ ] Display functions
    - [ ] `display_contribution()` - Same as v1
    - [ ] `display_facilitator_decision()` - Week 5
    - [ ] `display_convergence_metrics()` - Week 5
  - [ ] Pause/resume UI
    - [ ] Ask "Continue? (y/pause)"
    - [ ] If pause → save checkpoint, show resume command
    - [ ] If continue → proceed to next node

#### Entry Point Update

- [ ] Update `bo1/main.py`
  - [ ] Add `--resume` flag for session resumption
  - [ ] If resume: Load checkpoint, continue execution
  - [ ] Else: Create new session, run from start
  - [ ] Use `run_console_deliberation()` (new adapter)
  - [ ] Maintain same UX as v1 (backward compatible)

#### Benchmarking

- [ ] Create benchmark script (`scripts/benchmark_v1_v2.py`)
  - [ ] Run same problem in v1 (sequential)
  - [ ] Run same problem in v2 (LangGraph)
  - [ ] Measure:
    - [ ] Total execution time
    - [ ] Per-phase latency
    - [ ] Memory usage
    - [ ] Cost (should be identical)
  - [ ] Compare results
    - [ ] Target: <10% latency increase in v2
    - [ ] Document: Where latency added (graph overhead)
  - [ ] Generate report (CSV + charts)

#### Testing

- [ ] Test: Console adapter displays contributions
- [ ] Test: Pause/resume works
  - [ ] Pause after decompose, resume later
  - [ ] Verify checkpoint loaded correctly
  - [ ] Verify execution continues from checkpoint
- [ ] Test: Same UX as v1
  - [ ] User cannot tell difference (hidden migration)
  - [ ] All v1 console features work
- [ ] Benchmark: v1 vs v2 performance
  - [ ] Run 5 deliberations in each
  - [ ] Calculate average latency
  - [ ] Verify <10% increase

**Validation**:
- [ ] Console adapter works (displays correctly)
- [ ] Pause/resume works (checkpoint recovery)
- [ ] Benchmark passes (<10% latency increase)
- [ ] Same UX as v1 (user-invisible migration)

**Tests**:
```bash
pytest tests/test_console_adapter.py -v
python scripts/benchmark_v1_v2.py
```

**Go/No-Go Decision**:
- [ ] If benchmark passes (<10% increase): ✅ Proceed to Week 5
- [ ] If benchmark fails (>20% increase): ❌ Optimize hot paths, retry
- [ ] Document: Results in `zzz_project/WEEK4_BENCHMARK_RESULTS.md`

---

## Week 5 (Days 29-35): LangGraph Console Migration - Part 2

**Goal**: Complete console migration with full deliberation loop

**Status**: 0/42 tasks complete

### Day 29: Facilitator Node

**Value**: Orchestrate multi-round deliberation (continue/vote/moderator)

#### Facilitator Decision Node

- [ ] Create `facilitator_decide_node()` in `bo1/graph/nodes.py`
  - [ ] Convert graph state → DeliberationState
  - [ ] Call existing `FacilitatorAgent.decide_next_action()`
  - [ ] Update state with decision
  - [ ] Track cost in `phase_costs["facilitator_decision"]`
  - [ ] Return updated state with `facilitator_decision` field

#### Routing Based on Decision

- [ ] Update `bo1/graph/routers.py`
  - [ ] `route_facilitator_decision()` function
    - [ ] If decision.action == "vote" → return "vote"
    - [ ] If decision.action == "moderator" → return "moderator_intervene"
    - [ ] If decision.action == "continue" → return "persona_contribute"
    - [ ] If decision.action == "research" → return END (Week 5, Day 31)
  - [ ] Document: Decision types and routing logic

#### Testing

- [ ] Test: Facilitator node works
  - [ ] Call with initial round complete
  - [ ] Verify decision created (continue/vote/moderator)
  - [ ] Verify cost tracked
- [ ] Test: Routing works for each decision type
  - [ ] Mock decision.action = "vote" → routes to vote
  - [ ] Mock decision.action = "moderator" → routes to moderator
  - [ ] Mock decision.action = "continue" → routes to persona

**Validation**:
- [ ] Facilitator node executes correctly
- [ ] Routing logic handles all decision types
- [ ] Cost tracking works

**Tests**:
```bash
pytest tests/test_facilitator_node.py -v
pytest tests/test_facilitator_routing.py -v
```

---

### Day 30: Persona Contribution + Moderator Nodes

**Value**: Multi-round deliberation with moderation

#### Persona Contribution Node

- [ ] Create `persona_contribute_node()` in `bo1/graph/nodes.py`
  - [ ] Extract speaker from facilitator decision
  - [ ] Get persona profile by code
  - [ ] Reuse existing `DeliberationEngine._call_persona_async()`
  - [ ] Add contribution to state
  - [ ] Increment round_number
  - [ ] Track cost in `phase_costs[f"round_{round_number}_deliberation"]`
  - [ ] Return updated state

#### Moderator Intervention Node

- [ ] Create `moderator_intervene_node()` in `bo1/graph/nodes.py`
  - [ ] Call existing `ModeratorAgent.intervene()`
  - [ ] Add intervention to contributions
  - [ ] Track cost in `phase_costs["moderator_intervention"]`
  - [ ] Return updated state

#### Loop Edges

- [ ] Update `bo1/graph/config.py`
  - [ ] Add persona_contribute node
  - [ ] Add moderator_intervene node
  - [ ] Add edges: persona → check_convergence
  - [ ] Add edges: moderator → check_convergence
  - [ ] Add edge: check_convergence → facilitator (if continue)
  - [ ] Add edge: check_convergence → vote (if stop)

#### Testing

- [ ] Test: Persona contribution node works
  - [ ] Call with facilitator decision (continue)
  - [ ] Verify contribution created
  - [ ] Verify round_number incremented
  - [ ] Verify cost tracked
- [ ] Test: Moderator intervention node works
  - [ ] Call with facilitator decision (moderator)
  - [ ] Verify intervention created
  - [ ] Verify cost tracked
- [ ] Test: Multi-round loop works
  - [ ] Execute graph with 3 rounds
  - [ ] Verify loop: facilitator → persona → check → facilitator
  - [ ] Verify convergence stops loop

**Validation**:
- [ ] Persona node executes correctly
- [ ] Moderator node executes correctly
- [ ] Multi-round loop works (no infinite loops)
- [ ] Convergence stops loop correctly

**Tests**:
```bash
pytest tests/test_persona_node.py -v
pytest tests/test_moderator_node.py -v
pytest tests/test_multi_round_loop.py -v
```

---

### Day 31: Voting + Synthesis Nodes

**Value**: Complete deliberation with final recommendation

#### Vote Node

- [ ] Create `vote_node()` in `bo1/graph/nodes.py`
  - [ ] Call existing `VotingAgent.collect_votes()`
  - [ ] Store votes in state
  - [ ] Track cost in `phase_costs["voting"]`
  - [ ] Return updated state

#### Synthesis Node

- [ ] Create `synthesize_node()` in `bo1/graph/nodes.py`
  - [ ] Call existing `SynthesisAgent.synthesize()`
  - [ ] Store synthesis report in state
  - [ ] Track cost in `phase_costs["synthesis"]`
  - [ ] Mark phase as COMPLETE
  - [ ] Return updated state

#### Final Graph Assembly

- [ ] Update `bo1/graph/config.py`
  - [ ] Add vote node
  - [ ] Add synthesize node
  - [ ] Add edge: vote → synthesize
  - [ ] Add edge: synthesize → END
  - [ ] Verify complete graph:
    ```
    decompose → select → initial_round → facilitator
                                               ↓
                          ┌───────────────────┼──────┐
                          ↓                   ↓      ↓
                      continue            moderator vote
                          ↓                   ↓      ↓
                      persona             intervention |
                          ↓                   ↓        |
                      check_convergence ←─────┘        |
                          ↓                            |
                      (continue/stop)                  |
                          ↓                            |
                      facilitator ←────────────────────┘
                                                       ↓
                                                   synthesize → END
    ```

#### Testing

- [ ] Test: Vote node works
  - [ ] Call after deliberation complete
  - [ ] Verify votes collected
  - [ ] Verify cost tracked
- [ ] Test: Synthesis node works
  - [ ] Call after voting
  - [ ] Verify synthesis report created
  - [ ] Verify cost tracked
  - [ ] Verify phase = COMPLETE
- [ ] Test: Full graph end-to-end
  - [ ] Run complete deliberation (simple problem)
  - [ ] Verify all nodes execute in order
  - [ ] Verify final synthesis produced
  - [ ] Verify checkpoint created at each node

**Validation**:
- [ ] Vote node executes correctly
- [ ] Synthesis node executes correctly
- [ ] Full graph completes end-to-end
- [ ] All nodes tracked in phase_costs

**Tests**:
```bash
pytest tests/test_vote_node.py -v
pytest tests/test_synthesis_node.py -v
pytest tests/test_full_graph_end_to_end.py -v
```

---

### Day 32: Checkpoint Recovery + Resume

**Value**: Pause/resume works perfectly (critical for long deliberations)

#### Checkpoint Configuration

- [ ] Update `bo1/graph/config.py`
  - [ ] Add RedisSaver checkpointer
    ```python
    from langgraph.checkpoint.redis import RedisSaver

    checkpointer = RedisSaver(
        redis_url=os.getenv("REDIS_URL"),
        ttl_seconds=604800  # 7 days
    )

    graph = workflow.compile(
        checkpointer=checkpointer,
        recursion_limit=55
    )
    ```
  - [ ] Configure checkpoint strategy
    - [ ] Checkpoint after every node (default)
    - [ ] OR: Checkpoint only after expensive nodes (optimization)

#### Resume Implementation

- [ ] Update `bo1/interfaces/console.py`
  - [ ] Add resume logic to `run_console_deliberation()`
    - [ ] If session_id provided: Load checkpoint
    - [ ] Use `graph.aget_state(config)` to load
    - [ ] Verify checkpoint exists (handle not found)
    - [ ] Continue from last node
  - [ ] Display resume info
    - [ ] Show: Round, phase, personas, cost so far
    - [ ] Ask: Continue? (y/n)
  - [ ] Pause logic
    - [ ] At checkpoint: Ask "Continue or pause?"
    - [ ] If pause: Exit gracefully, show resume command

#### Testing

- [ ] Test: Checkpoint created after each node
  - [ ] Run graph with checkpointer
  - [ ] Verify checkpoint in Redis after decompose
  - [ ] Verify checkpoint after select
  - [ ] Verify checkpoint after each round
- [ ] Test: Resume from checkpoint works
  - [ ] Pause after decompose
  - [ ] Resume later
  - [ ] Verify graph continues from select (not restart)
- [ ] Test: Resume from middle of deliberation
  - [ ] Pause after Round 2
  - [ ] Resume later
  - [ ] Verify continues from Round 3
- [ ] Test: Multiple resume sessions
  - [ ] Pause 3 times, resume 3 times
  - [ ] Verify deliberation completes correctly

**Validation**:
- [ ] Checkpoints created at every node
- [ ] Resume works from any checkpoint
- [ ] No data loss on pause/resume
- [ ] Cost tracking preserved across resume

**Tests**:
```bash
pytest tests/test_checkpoint_recovery.py -v
pytest tests/test_resume_session.py -v
```

---

### Day 33: Cost Tracking Per Phase

**Value**: Admin visibility into where $ is spent

#### Phase Cost Tracking

- [ ] Update all nodes to track phase costs
  - [ ] In each node: `state["metrics"]["phase_costs"][phase_name] += cost`
  - [ ] Phase names:
    - [ ] "problem_decomposition"
    - [ ] "persona_selection"
    - [ ] "initial_round"
    - [ ] "round_1_deliberation", "round_2_deliberation", etc.
    - [ ] "moderator_intervention_contrarian", etc.
    - [ ] "voting"
    - [ ] "synthesis"
  - [ ] Detailed phase metrics in `state["phase_metrics"]` (list)
    - [ ] phase, node, persona_code, model, tokens, cost, duration

#### Cost Analytics

- [ ] Create `bo1/graph/analytics.py`
  - [ ] `get_phase_costs()` - Extract from state
  - [ ] `calculate_cost_breakdown()` - Pie chart data
  - [ ] `export_phase_metrics_csv()` - For analysis
  - [ ] `export_phase_metrics_json()` - For archival

#### Console Display

- [ ] Update `bo1/ui/console.py`
  - [ ] Add `print_phase_costs()` method
    - [ ] Display Rich table with cost breakdown
    - [ ] Show: Phase, Cost, % of Total, Tokens
    - [ ] Highlight most expensive phases
  - [ ] Call at end of deliberation
    - [ ] After synthesis, before export

#### Testing

- [ ] Test: Phase costs tracked correctly
  - [ ] Run full deliberation
  - [ ] Verify all phases have costs
  - [ ] Verify sum equals total_cost
- [ ] Test: Detailed metrics captured
  - [ ] Verify phase_metrics list has all LLM calls
  - [ ] Verify each entry has: phase, node, cost, tokens, duration
- [ ] Test: Console display works
  - [ ] Verify table renders correctly
  - [ ] Verify percentages calculated correctly

**Validation**:
- [ ] All phases tracked in phase_costs
- [ ] Detailed metrics captured in phase_metrics
- [ ] Console displays breakdown correctly
- [ ] CSV/JSON export works

**Tests**:
```bash
pytest tests/test_phase_cost_tracking.py -v
pytest tests/test_cost_analytics.py -v
```

---

### Day 34: Final Validation + Migration

**Value**: v2 console matches v1 feature parity

#### Feature Parity Checklist

- [ ] Compare v1 vs v2 features
  - [ ] Problem decomposition: ✅ Same
  - [ ] Persona selection: ✅ Same
  - [ ] Multi-round deliberation: ✅ Same
  - [ ] Voting: ✅ Same
  - [ ] Synthesis: ✅ Same
  - [ ] Pause/resume: ✅ **NEW** (v2 only)
  - [ ] Cost tracking: ✅ Enhanced (per-phase)
  - [ ] Export (JSON, Markdown): ✅ Same

#### Migrate Main Entry Point

- [ ] Update `bo1/main.py` to use LangGraph by default
  - [ ] Remove v1 orchestration code (or keep as `--legacy` flag)
  - [ ] Use `run_console_deliberation()` (LangGraph adapter)
  - [ ] Add `--resume` flag for session resumption
  - [ ] Maintain backward compatibility (same CLI interface)
  - [ ] Document: How to switch between v1/v2 (if legacy kept)

#### Documentation

- [ ] Update `CLAUDE.md`
  - [ ] Change: "v1 is console-only" → "Console uses LangGraph"
  - [ ] Add: Pause/resume instructions
  - [ ] Add: Loop prevention guarantees (5 layers)
  - [ ] Add: Kill switch documentation
- [ ] Update `README.md`
  - [ ] Add: How to resume sessions
  - [ ] Add: New features (pause/resume, checkpoint recovery)
  - [ ] Update: Architecture diagram (show LangGraph)
- [ ] Create `zzz_project/LANGGRAPH_MIGRATION_COMPLETE.md`
  - [ ] Document: What changed
  - [ ] Benchmark results (v1 vs v2 latency)
  - [ ] Feature comparison table
  - [ ] Migration lessons learned

#### Testing

- [ ] Run full integration test suite
  - [ ] `pytest tests/test_integration_day7.py -v` (v1 test)
  - [ ] Update for v2 (should still pass)
- [ ] Run scenario tests (10+ solopreneur problems)
  - [ ] Verify: 5-15 min per deliberation
  - [ ] Verify: <$1 per session
  - [ ] Verify: >70% consensus rate
  - [ ] Compare: v1 vs v2 results (should be identical)

**Validation**:
- [ ] All v1 features work in v2
- [ ] Pause/resume works (v2 enhancement)
- [ ] Cost tracking enhanced (per-phase)
- [ ] Integration tests pass
- [ ] Scenario tests pass (same results as v1)

**Tests**:
```bash
pytest tests/test_integration_v2.py -v
pytest tests/test_scenario_v2.py -v
python scripts/compare_v1_v2_results.py
```

---

### Day 35: Week 5 Retrospective + Pre-commit

**Value**: Clean, documented, tested code ready for Week 6

#### Code Quality

- [ ] Run full linting and formatting
  ```bash
  make pre-commit  # lint + format + typecheck
  ```
- [ ] Fix all linting errors
- [ ] Fix all type errors (mypy)
- [ ] Ensure 100% test coverage for graph module
  ```bash
  pytest --cov=bo1/graph tests/ --cov-report=html
  ```

#### Performance Review

- [ ] Re-run benchmarks (v1 vs v2)
  - [ ] Verify still <10% latency increase
  - [ ] If degraded: Profile and optimize
  - [ ] Document results in `zzz_project/WEEK5_BENCHMARK_RESULTS.md`

#### Documentation Review

- [ ] Review all new docstrings (graph, nodes, safety)
- [ ] Ensure all functions have type hints
- [ ] Update architecture diagrams (if needed)
- [ ] Verify examples in docs work

#### Retrospective

- [ ] Create `zzz_project/WEEK5_RETROSPECTIVE.md`
  - [ ] What went well
  - [ ] What was challenging
  - [ ] Unexpected issues
  - [ ] Lessons learned
  - [ ] Adjustments for Week 6

**Validation**:
- [ ] All pre-commit checks pass
- [ ] Test coverage >95% for graph module
- [ ] Documentation complete and accurate
- [ ] Retrospective written

**Go/No-Go for Week 6**:
- [ ] ✅ Benchmarks pass (<10% increase)
- [ ] ✅ All tests pass (unit + integration)
- [ ] ✅ Code quality checks pass
- [ ] ✅ Documentation complete

---

## Week 6 (Days 36-42): Web API Adapter - FastAPI + SSE

**Goal**: Web API serves LangGraph backend with real-time streaming

**Status**: 0/42 tasks complete

### Day 36: FastAPI Setup + Health Checks

**Value**: API infrastructure ready for deliberation endpoints

#### FastAPI Application

- [ ] Create `backend/` directory structure
  ```bash
  mkdir -p backend/api
  touch backend/api/__init__.py
  touch backend/api/main.py
  touch backend/api/deliberation.py
  touch backend/api/health.py
  ```
- [ ] Create `backend/api/main.py`
  - [ ] Initialize FastAPI app
  - [ ] Configure CORS (for SvelteKit frontend)
  - [ ] Add routers (deliberation, health, admin)
  - [ ] Add middleware (logging, error handling)
  - [ ] Configure environment (dev/prod)

#### Health Check Endpoints

- [ ] Create `backend/api/health.py`
  - [ ] `GET /api/health` - Basic health check (200 OK)
  - [ ] `GET /api/health/db` - PostgreSQL connection check
  - [ ] `GET /api/health/redis` - Redis connection check
  - [ ] `GET /api/health/anthropic` - Anthropic API key valid
  - [ ] Return: Status (healthy/unhealthy), details (version, uptime)

#### Docker Configuration

- [ ] Update `docker-compose.yml`
  - [ ] Add `api` service (FastAPI)
  - [ ] Expose port 8000
  - [ ] Mount backend/ volume (hot reload)
  - [ ] Add environment variables
  - [ ] Depends on: postgres, redis
- [ ] Create `backend/Dockerfile`
  - [ ] Base: python:3.12-slim
  - [ ] Install uv
  - [ ] Copy pyproject.toml, install dependencies
  - [ ] Copy backend/ code
  - [ ] CMD: uvicorn api.main:app --reload --host 0.0.0.0

#### Testing

- [ ] Test: FastAPI app starts
  - [ ] `curl http://localhost:8000/api/health`
  - [ ] Verify 200 OK response
- [ ] Test: Health checks work
  - [ ] `/api/health/db` - Verify DB connection
  - [ ] `/api/health/redis` - Verify Redis connection
  - [ ] `/api/health/anthropic` - Verify API key valid
- [ ] Test: CORS configured correctly
  - [ ] Send OPTIONS request from frontend origin
  - [ ] Verify CORS headers present

**Validation**:
- [ ] FastAPI app runs successfully
- [ ] All health checks pass
- [ ] CORS allows frontend access
- [ ] Docker hot reload works

**Tests**:
```bash
pytest backend/tests/test_health.py -v
curl http://localhost:8000/api/health
```

#### Supabase Auth Setup
- [ ] Create Supabase project (free tier)
- [ ] Enable social OAuth providers:
  - [ ] Google OAuth (create Google Cloud project)
  - [ ] LinkedIn OAuth (create LinkedIn app)
  - [ ] GitHub OAuth (create GitHub OAuth app)
- [ ] Configure redirect URLs (http://localhost:3000/auth/callback)
- [ ] Get Supabase credentials (URL, anon key, service role key)
- [ ] Add to .env: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
- [ ] Create auth middleware (backend/api/middleware/auth.py)
  ```python
  from supabase import create_client
  async def verify_jwt(token: str) -> dict:
      supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
      user = supabase.auth.get_user(token)
      return user
  ```
- [ ] Test: Sign up with Google OAuth
- [ ] Test: Sign up with LinkedIn OAuth
- [ ] Test: Sign up with GitHub OAuth
- [ ] Test: Email verification flow
- [ ] Test: Password reset flow
- [ ] Test: JWT token refresh

**Validation**:
- [ ] Can sign up with all 3 OAuth providers
- [ ] JWT tokens validated correctly
- [ ] Protected endpoints return 401 without token

---

### Day 37: Session Management API

**Value**: Create, list, view deliberation sessions

#### Session Models

- [ ] Create `backend/api/models.py`
  - [ ] `CreateSessionRequest` (Pydantic)
    - [ ] problem_statement: str
    - [ ] problem_context: dict | None
  - [ ] `SessionResponse` (Pydantic)
    - [ ] id: str (session_id)
    - [ ] status: str (active, completed, failed)
    - [ ] phase: str (current_phase)
    - [ ] created_at: datetime
    - [ ] updated_at: datetime
    - [ ] problem_statement: str (truncated for list view)

#### Session Endpoints

- [ ] Create `backend/api/deliberation.py`
  - [ ] `POST /api/v1/sessions` - Create new session
    - [ ] Validate request body
    - [ ] Generate session_id (UUID)
    - [ ] Create initial graph state
    - [ ] Save to Redis
    - [ ] Return SessionResponse
  - [ ] `GET /api/v1/sessions` - List user's sessions
    - [ ] Require authentication (Week 7)
    - [ ] For now: List all sessions (no auth)
    - [ ] Filter by status (query param)
    - [ ] Paginate (limit, offset)
    - [ ] Return list[SessionResponse]
  - [ ] `GET /api/v1/sessions/{session_id}` - Get session details
    - [ ] Load from Redis
    - [ ] Return full DeliberationGraphState (JSON)

#### Session Storage

- [ ] Update `bo1/state/redis_manager.py`
  - [ ] Add `list_sessions()` method
    - [ ] Scan Redis for `session:*` keys
    - [ ] Return list of session_ids
  - [ ] Add `load_metadata()` method
    - [ ] Load session metadata (status, phase, timestamps)
    - [ ] Faster than loading full state
  - [ ] Add `save_metadata()` method
    - [ ] Update metadata only (not full state)

#### Testing

- [ ] Test: Create session endpoint
  - [ ] POST with valid problem
  - [ ] Verify session_id returned
  - [ ] Verify session saved to Redis
- [ ] Test: List sessions endpoint
  - [ ] Create 3 sessions
  - [ ] GET /api/v1/sessions
  - [ ] Verify 3 sessions returned
- [ ] Test: Get session details
  - [ ] GET /api/v1/sessions/{id}
  - [ ] Verify full state returned

**Validation**:
- [ ] Session creation works
- [ ] Session listing works (paginated)
- [ ] Session details endpoint works
- [ ] Redis storage works correctly

**Tests**:
```bash
pytest backend/tests/test_sessions_api.py -v
```

---

### Day 38: SSE Streaming Implementation

**Value**: Real-time deliberation updates to web UI

#### SSE Endpoint

- [ ] Add SSE streaming endpoint
  - [ ] `GET /api/v1/sessions/{session_id}/stream`
    - [ ] Validate session exists
    - [ ] Return `StreamingResponse` (media_type="text/event-stream")
    - [ ] Stream graph events to client
  - [ ] Event types:
    - [ ] `node_start` - Node execution started
    - [ ] `node_end` - Node execution completed
    - [ ] `contribution` - Persona contributed
    - [ ] `facilitator_decision` - Facilitator decided
    - [ ] `convergence` - Convergence check result
    - [ ] `complete` - Deliberation finished

#### Graph Streaming

- [ ] Update `bo1/graph/execution.py`
  - [ ] Add `stream_deliberation()` function
    - [ ] Use `graph.astream_events()`
    - [ ] Yield events as JSON strings
    - [ ] Format: `data: {json}\n\n`
  - [ ] Filter events for client
    - [ ] Send: node_start, node_end, errors
    - [ ] Skip: Internal state updates

#### Event Formatting

- [ ] Create `backend/api/events.py`
  - [ ] `format_sse_event()` function
    - [ ] Input: event dict
    - [ ] Output: SSE-formatted string
    - [ ] Add event type, data, timestamp
  - [ ] Event builders:
    - [ ] `node_start_event()`
    - [ ] `node_end_event()`
    - [ ] `contribution_event()`
    - [ ] `error_event()`

#### Testing

- [ ] Test: SSE endpoint returns events
  - [ ] Create session, start deliberation
  - [ ] Connect SSE client
  - [ ] Verify events received in order
- [ ] Test: Event formatting correct
  - [ ] Verify SSE format: `data: {json}\n\n`
  - [ ] Verify JSON parseable
- [ ] Test: Client reconnection works
  - [ ] Disconnect client mid-stream
  - [ ] Reconnect
  - [ ] Verify events resume correctly

**Validation**:
- [ ] SSE streaming works
- [ ] Events formatted correctly
- [ ] Client receives real-time updates
- [ ] Reconnection works

**Tests**:
```bash
pytest backend/tests/test_sse_streaming.py -v
```

---

### Day 39: Deliberation Control Endpoints

**Value**: Start, pause, kill deliberations via API

#### Start Deliberation

- [ ] Add `POST /api/v1/sessions/{session_id}/start`
  - [ ] Validate session exists and not already running
  - [ ] Start deliberation in background (asyncio.create_task)
  - [ ] Track in SessionManager.active_executions
  - [ ] Return 202 Accepted (async started)

#### Pause Deliberation

- [ ] Add `POST /api/v1/sessions/{session_id}/pause`
  - [ ] Mark session as paused (metadata)
  - [ ] Checkpoint auto-saved by LangGraph
  - [ ] Return pause confirmation

#### Kill Deliberation

- [ ] Add `POST /api/v1/sessions/{session_id}/kill`
  - [ ] Require: User owns session (auth check)
  - [ ] Call SessionManager.kill_session()
  - [ ] Return kill confirmation
  - [ ] Include: Audit trail (who, when, why)

#### Resume Deliberation

- [ ] Add `POST /api/v1/sessions/{session_id}/resume`
  - [ ] Load checkpoint from Redis
  - [ ] Continue graph execution
  - [ ] Update metadata (paused = false)
  - [ ] Return resume confirmation

#### Testing

- [ ] Test: Start deliberation
  - [ ] POST /start
  - [ ] Verify background task created
  - [ ] Verify 202 Accepted response
- [ ] Test: Pause deliberation
  - [ ] Start, then pause
  - [ ] Verify checkpoint saved
  - [ ] Verify metadata updated
- [ ] Test: Kill deliberation
  - [ ] Start, then kill
  - [ ] Verify task canceled
  - [ ] Verify audit trail logged
- [ ] Test: Resume deliberation
  - [ ] Pause, then resume
  - [ ] Verify continues from checkpoint
  - [ ] Verify no data loss

**Validation**:
- [ ] Start endpoint works (async background task)
- [ ] Pause endpoint works (checkpoint saved)
- [ ] Kill endpoint works (audit trail logged)
- [ ] Resume endpoint works (checkpoint loaded)

**Tests**:
```bash
pytest backend/tests/test_deliberation_control.py -v
```

---

### Day 40: Admin API Endpoints

**Value**: Admin monitoring and control

#### Admin Session Monitoring

- [ ] Add `GET /api/admin/sessions/active`
  - [ ] List all active sessions (any user)
  - [ ] Include: user_id, session_id, duration, cost, phase
  - [ ] Calculate: vs median (runaway detection)
  - [ ] Return: Top 10 longest + top 10 most expensive
- [ ] Add `GET /api/admin/sessions/{session_id}/full`
  - [ ] Return complete session state
  - [ ] Include: All contributions, votes, costs, tokens
  - [ ] Calculate: Cache hit rate, per-phase costs

#### Admin Kill Switches

- [ ] Add `POST /api/admin/sessions/{session_id}/kill`
  - [ ] Require admin role
  - [ ] Call SessionManager.admin_kill_session()
  - [ ] No ownership check (admin can kill any)
  - [ ] Log with admin user_id
- [ ] Add `POST /api/admin/sessions/kill-all`
  - [ ] Emergency shutdown (system maintenance)
  - [ ] Require: confirm=true query param
  - [ ] Call SessionManager.admin_kill_all_sessions()
  - [ ] Return: count of killed sessions

#### Admin Middleware

- [ ] Create `backend/api/middleware/admin.py`
  - [ ] `require_admin()` dependency
    - [ ] Check: X-Admin-Key header
    - [ ] Compare with ADMIN_API_KEY env var
    - [ ] Raise 403 if not admin
  - [ ] For MVP: Simple API key auth
  - [ ] For v2: Role-based auth (Supabase)

#### Testing

- [ ] Test: Admin can list active sessions
  - [ ] Start 3 sessions
  - [ ] GET /api/admin/sessions/active
  - [ ] Verify all 3 returned
- [ ] Test: Admin can view full session
  - [ ] GET /api/admin/sessions/{id}/full
  - [ ] Verify all data returned (not just metadata)
- [ ] Test: Admin can kill any session
  - [ ] Start session (user_1)
  - [ ] Admin kills session
  - [ ] Verify success
- [ ] Test: Admin can kill all sessions
  - [ ] Start 5 sessions
  - [ ] POST /api/admin/sessions/kill-all?confirm=true
  - [ ] Verify all 5 killed

**Validation**:
- [ ] Admin endpoints work
- [ ] Admin auth required (API key)
- [ ] Admin kill switches work
- [ ] Audit trail logged

**Tests**:
```bash
pytest backend/tests/test_admin_api.py -v
```

---

### Day 41: API Documentation (FastAPI Auto-Docs)

**Value**: API documentation for frontend developers

#### Enable FastAPI Auto-Docs

- [ ] Configure OpenAPI schema
  - [ ] Add title, version, description to FastAPI app
  - [ ] Add tags for route grouping (sessions, admin, health)
  - [ ] Add response models for all endpoints
- [ ] Add docstrings to all endpoints
  - [ ] Summary (one line)
  - [ ] Description (detailed)
  - [ ] Parameters (path, query, body)
  - [ ] Response examples

#### Enhance API Models

- [ ] Add examples to Pydantic models
  ```python
  class CreateSessionRequest(BaseModel):
      problem_statement: str = Field(..., example="Should we invest $500K in...")
      problem_context: dict | None = Field(None, example={"budget": 500000})
  ```
- [ ] Add descriptions to fields
  ```python
  class SessionResponse(BaseModel):
      id: str = Field(..., description="Unique session identifier (UUID)")
      status: str = Field(..., description="Current session status")
  ```

#### Interactive Docs

- [ ] Access Swagger UI at `/docs`
  - [ ] Verify all endpoints listed
  - [ ] Verify request/response schemas
  - [ ] Test endpoints directly from browser
- [ ] Access ReDoc at `/redoc`
  - [ ] Verify clean documentation layout
  - [ ] Verify examples displayed correctly

#### Testing

- [ ] Test: Swagger UI loads
  - [ ] Visit http://localhost:8000/docs
  - [ ] Verify UI renders
- [ ] Test: Can execute requests from Swagger
  - [ ] Try POST /api/v1/sessions
  - [ ] Verify request works
- [ ] Test: ReDoc loads
  - [ ] Visit http://localhost:8000/redoc
  - [ ] Verify docs readable

**Validation**:
- [ ] Swagger UI works
- [ ] ReDoc works
- [ ] All endpoints documented
- [ ] Examples helpful

**Tests**:
Manual testing via browser (no automated tests needed)

---

### Day 42: Week 6 Integration + Pre-commit

**Value**: API stable, documented, ready for Week 7

#### Full API Integration Test

- [ ] Create `backend/tests/test_api_integration.py`
  - [ ] Test: Create session
  - [ ] Test: Start deliberation
  - [ ] Test: Stream events (SSE)
  - [ ] Test: Pause deliberation
  - [ ] Test: Resume deliberation
  - [ ] Test: Get session details
  - [ ] Test: Kill deliberation
  - [ ] Test: Admin endpoints (active sessions, kill)
  - [ ] Verify: End-to-end flow works

#### Performance Testing

- [ ] Test concurrent sessions
  - [ ] Start 10 sessions simultaneously
  - [ ] Verify: No conflicts, no crashes
  - [ ] Measure: Response times (<500ms)
- [ ] Test SSE scalability
  - [ ] Connect 50 SSE clients
  - [ ] Verify: All receive events
  - [ ] Measure: Event latency (<100ms)

#### Code Quality

- [ ] Run pre-commit checks
  ```bash
  make pre-commit  # lint + format + typecheck
  ```
- [ ] Fix all issues
- [ ] Ensure 100% test coverage for API
  ```bash
  pytest --cov=backend/api tests/ --cov-report=html
  ```

#### Documentation

- [ ] Update `README.md`
  - [ ] Add: API endpoints documentation
  - [ ] Add: How to run API (`make up`)
  - [ ] Add: How to access Swagger UI
- [ ] Create `zzz_project/WEEK6_API_SUMMARY.md`
  - [ ] Endpoints implemented
  - [ ] SSE streaming details
  - [ ] Admin endpoints
  - [ ] Performance metrics

**Validation**:
- [ ] Full integration test passes
- [ ] Concurrent sessions work
- [ ] SSE streaming scalable (50 clients)
- [ ] All pre-commit checks pass
- [ ] Documentation complete

**Tests**:
```bash
pytest backend/tests/test_api_integration.py -v
python scripts/test_concurrent_sessions.py
```

**Go/No-Go for Week 7**:
- [ ] ✅ Integration tests pass
- [ ] ✅ Performance tests pass (<500ms API latency)
- [ ] ✅ SSE streaming works (50+ clients)
- [ ] ✅ Documentation complete

---

## Week 7 (Days 43-49): Web UI Foundation - SvelteKit + Real-time

**Goal**: Basic web UI with real-time deliberation streaming

**Status**: 0/42 tasks complete

### Day 43: SvelteKit Setup + Routing

**Value**: Frontend foundation ready

#### SvelteKit Initialization

- [ ] Create SvelteKit project
  ```bash
  npm create svelte@latest frontend
  # Choose: SvelteKit demo app
  # TypeScript: Yes
  # ESLint, Prettier: Yes
  ```
- [ ] Install dependencies
  ```bash
  cd frontend
  npm install
  ```
- [ ] Configure for SSR + CSR
  - [ ] Update `svelte.config.js`
  - [ ] Configure adapter (node adapter for DigitalOcean)
  - [ ] Configure base URL for API

#### Directory Structure

- [ ] Create route structure
  ```bash
  mkdir -p src/routes/(app)
  mkdir -p src/routes/(auth)
  mkdir -p src/routes/api/v1
  mkdir -p src/lib/components
  mkdir -p src/lib/stores
  mkdir -p src/lib/api
  ```
- [ ] Routes:
  - [ ] `/` - Landing page (public)
  - [ ] `/login` - Login page (auth)
  - [ ] `/dashboard` - User dashboard (app)
  - [ ] `/sessions/new` - Create session (app)
  - [ ] `/sessions/[id]` - View session (app)

#### Tailwind CSS Setup

- [ ] Install Tailwind CSS
  ```bash
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
- [ ] Configure `tailwind.config.js`
  - [ ] Add content paths
  - [ ] Add custom theme colors
  - [ ] Add dark mode support
- [ ] Create `src/app.css`
  - [ ] Import Tailwind directives
  - [ ] Add global styles

#### Testing

- [ ] Test: SvelteKit dev server starts
  ```bash
  npm run dev
  ```
  - [ ] Visit http://localhost:5173
  - [ ] Verify demo page loads
- [ ] Test: Tailwind CSS works
  - [ ] Add `<div class="bg-blue-500 text-white p-4">Test</div>`
  - [ ] Verify styling applied
- [ ] Test: TypeScript works
  - [ ] Create component with TypeScript
  - [ ] Verify type checking works

#### Cookie Consent Banner
- [ ] Install cookie consent library: `npm install svelte-cookie-consent`
- [ ] Create consent banner component (src/lib/components/CookieConsent.svelte)
- [ ] Categories:
  - [ ] Essential (authentication) - always enabled
  - [ ] Analytics (opt-in) - disabled by default
- [ ] Show banner on first visit
- [ ] Respect user choice (don't load analytics if declined)
- [ ] Store preference in localStorage
- [ ] Test: Verify analytics not loaded if user declines

**Validation**:
- [ ] SvelteKit runs successfully
- [ ] Tailwind CSS configured
- [ ] TypeScript configured
- [ ] Route structure created
- [ ] Banner shows on first visit
- [ ] User can accept/decline analytics
- [ ] Preference persisted across sessions

**Tests**:
Manual testing via browser

---

### Day 44: API Client + State Management

**Value**: Connect frontend to backend API

#### API Client

- [ ] Create `src/lib/api/client.ts`
  - [ ] `ApiClient` class
    - [ ] `baseUrl` from environment variable
    - [ ] `fetch` wrapper with error handling
    - [ ] Methods:
      - [ ] `createSession(problem)`
      - [ ] `listSessions()`
      - [ ] `getSession(id)`
      - [ ] `startDeliberation(id)`
      - [ ] `pauseDeliberation(id)`
      - [ ] `killDeliberation(id)`

#### SSE Client

- [ ] Create `src/lib/api/sse.ts`
  - [ ] `SSEClient` class
    - [ ] `connect(sessionId)` - Open EventSource
    - [ ] `onEvent(callback)` - Handle events
    - [ ] `close()` - Cleanup
  - [ ] Event handlers:
    - [ ] `node_start` → Update UI
    - [ ] `contribution` → Add to feed
    - [ ] `facilitator_decision` → Update phase
    - [ ] `complete` → Redirect to results

#### Svelte Stores

- [ ] Create `src/lib/stores/session.ts`
  - [ ] `sessionStore` (writable store)
    - [ ] State: `{ id, status, phase, contributions, metrics }`
    - [ ] Actions: `createSession()`, `loadSession()`, `updateContribution()`
  - [ ] `sseStore` (custom store)
    - [ ] Connect/disconnect SSE
    - [ ] Update sessionStore from events

#### Testing

- [ ] Test: API client works
  - [ ] Create session via API client
  - [ ] Verify session created
- [ ] Test: SSE client connects
  - [ ] Connect to SSE endpoint
  - [ ] Verify events received
- [ ] Test: Stores update correctly
  - [ ] Create session
  - [ ] Verify sessionStore updated
  - [ ] Connect SSE
  - [ ] Verify store updates from events

**Validation**:
- [ ] API client works (all methods)
- [ ] SSE client connects and receives events
- [ ] Stores manage state correctly

**Tests**:
```bash
npm run test:unit  # Vitest
```

---

### Day 45: Create Session Page

**Value**: User can create new deliberation

#### Session Creation Form

- [ ] Create `src/routes/(app)/sessions/new/+page.svelte`
  - [ ] Form with textarea (problem_statement)
  - [ ] Optional fields (budget, timeline, constraints)
  - [ ] Validation (min 50 chars)
  - [ ] Submit button
- [ ] Handle submission
  - [ ] Call `apiClient.createSession()`
  - [ ] On success: Redirect to `/sessions/[id]`
  - [ ] On error: Show error message

#### UI Components

- [ ] Create `src/lib/components/ProblemForm.svelte`
  - [ ] Textarea with character count
  - [ ] Optional context fields (collapsible)
  - [ ] Submit button with loading state
- [ ] Create `src/lib/components/ErrorMessage.svelte`
  - [ ] Display API errors
  - [ ] Dismissable
  - [ ] Styled with Tailwind

#### Testing

- [ ] Test: Form renders
  - [ ] Visit /sessions/new
  - [ ] Verify form displays
- [ ] Test: Form validation works
  - [ ] Submit empty form
  - [ ] Verify error shown
  - [ ] Submit valid form
  - [ ] Verify redirect
- [ ] Test: Error handling works
  - [ ] Mock API error
  - [ ] Verify error message shown

**Validation**:
- [ ] Form renders correctly
- [ ] Validation works (client-side)
- [ ] Submission works (API call)
- [ ] Error handling works

**Tests**:
Manual testing + Playwright E2E (Week 13)

---

### Day 46: Real-Time Deliberation View

**Value**: Watch deliberation unfold in real-time

#### Deliberation Page

- [ ] Create `src/routes/(app)/sessions/[id]/+page.svelte`
  - [ ] Load session data (`+page.server.ts`)
  - [ ] Connect SSE client on mount
  - [ ] Display session header (problem, status, phase)
  - [ ] Display contribution feed (real-time)
  - [ ] Display metrics (cost, rounds, duration)

#### Contribution Feed

- [ ] Create `src/lib/components/ContributionFeed.svelte`
  - [ ] List of contributions (scrollable)
  - [ ] Each contribution:
    - [ ] Persona avatar + name
    - [ ] Content (markdown rendered)
    - [ ] Timestamp
  - [ ] Auto-scroll to bottom on new contribution
  - [ ] Animate new contributions (slide in)

#### SSE Integration

- [ ] On mount: Connect SSE
  ```typescript
  onMount(() => {
      const sse = new SSEClient();
      sse.connect(sessionId);
      sse.onEvent((event) => {
          if (event.type === 'contribution') {
              sessionStore.addContribution(event.data);
          }
      });
      return () => sse.close();  // Cleanup
  });
  ```

#### Testing

- [ ] Test: Page loads session data
  - [ ] Visit /sessions/{id}
  - [ ] Verify session data displayed
- [ ] Test: SSE connects automatically
  - [ ] Verify SSE client created
  - [ ] Verify events update UI
- [ ] Test: Contribution feed updates
  - [ ] Start deliberation
  - [ ] Verify contributions appear in real-time
  - [ ] Verify auto-scroll works

**Validation**:
- [ ] Page loads session correctly
- [ ] SSE connects on mount
- [ ] Contribution feed updates in real-time
- [ ] UI smooth (no jank)

**Tests**:
Manual testing + Playwright E2E

---

### Day 47: Session Dashboard

**Value**: User can view all their sessions

#### Dashboard Page

- [ ] Create `src/routes/(app)/dashboard/+page.svelte`
  - [ ] Load user sessions (`+page.server.ts`)
  - [ ] Display session cards (grid layout)
  - [ ] Filter by status (active, completed)
  - [ ] Sort by date (newest first)
  - [ ] Pagination (10 per page)

#### Session Card

- [ ] Create `src/lib/components/SessionCard.svelte`
  - [ ] Problem title (truncated)
  - [ ] Status badge (color-coded)
  - [ ] Created date (relative time)
  - [ ] Metrics (rounds, cost)
  - [ ] Actions:
    - [ ] "View" → Go to /sessions/[id]
    - [ ] "Resume" (if paused)
    - [ ] "Delete" (confirm modal)

#### Filters & Search

- [ ] Add status filter (dropdown)
  - [ ] Options: All, Active, Completed, Failed
  - [ ] Update URL query param
  - [ ] Reload sessions on change
- [ ] Add search (input)
  - [ ] Search by problem statement
  - [ ] Debounced (500ms)
  - [ ] Update results live

#### Testing

- [ ] Test: Dashboard loads sessions
  - [ ] Create 3 sessions
  - [ ] Visit /dashboard
  - [ ] Verify 3 cards displayed
- [ ] Test: Status filter works
  - [ ] Select "Completed"
  - [ ] Verify only completed sessions shown
- [ ] Test: Search works
  - [ ] Type query
  - [ ] Verify filtered sessions shown

**Validation**:
- [ ] Dashboard displays sessions
- [ ] Filters work correctly
- [ ] Search works (debounced)
- [ ] Pagination works (if >10 sessions)

**Tests**:
Manual testing + Playwright E2E

---

### Day 48: Control Actions (Pause, Resume, Kill)

**Value**: User can control deliberations

#### Action Buttons

- [ ] Add to `/sessions/[id]/+page.svelte`
  - [ ] "Pause" button (if status=active)
  - [ ] "Resume" button (if status=paused)
  - [ ] "Kill" button (with confirmation)
  - [ ] Disable buttons during loading

#### Pause Deliberation

- [ ] On click "Pause":
  - [ ] Call `apiClient.pauseDeliberation(id)`
  - [ ] Update sessionStore (status=paused)
  - [ ] Show toast notification ("Session paused")
  - [ ] Disconnect SSE

#### Resume Deliberation

- [ ] On click "Resume":
  - [ ] Call `apiClient.resumeDeliberation(id)`
  - [ ] Update sessionStore (status=active)
  - [ ] Reconnect SSE
  - [ ] Show toast ("Session resumed")

#### Kill Deliberation

- [ ] On click "Kill":
  - [ ] Show confirmation modal
    - [ ] "Are you sure? This cannot be undone."
    - [ ] Input: Reason (optional)
  - [ ] On confirm:
    - [ ] Call `apiClient.killDeliberation(id, reason)`
    - [ ] Update sessionStore (status=killed)
    - [ ] Disconnect SSE
    - [ ] Show toast ("Session terminated")

#### Toast Notifications

- [ ] Create `src/lib/components/Toast.svelte`
  - [ ] Display at top-right
  - [ ] Auto-dismiss after 3 seconds
  - [ ] Types: success, error, info, warning
  - [ ] Animate (slide in/out)

#### Testing

- [ ] Test: Pause button works
  - [ ] Click pause
  - [ ] Verify API called
  - [ ] Verify status updated
- [ ] Test: Resume button works
  - [ ] Pause, then resume
  - [ ] Verify SSE reconnects
- [ ] Test: Kill button works
  - [ ] Click kill
  - [ ] Verify confirmation modal shown
  - [ ] Confirm kill
  - [ ] Verify session terminated

**Validation**:
- [ ] Pause works (checkpoint saved)
- [ ] Resume works (SSE reconnects)
- [ ] Kill works (confirmation required)
- [ ] Toast notifications display

**Tests**:
Manual testing + Playwright E2E

---

### Day 49: Week 7 Polish + Pre-commit

**Value**: UI polished, responsive, accessible

#### Responsive Design

- [ ] Test on mobile (375px width)
  - [ ] Adjust: Session cards stack vertically
  - [ ] Adjust: Font sizes readable
  - [ ] Adjust: Buttons full-width on mobile
- [ ] Test on tablet (768px width)
  - [ ] Adjust: 2-column grid for session cards
  - [ ] Adjust: Navigation responsive
- [ ] Test on desktop (1440px width)
  - [ ] Adjust: 3-column grid for session cards
  - [ ] Adjust: Max-width container

#### Accessibility

- [ ] Add ARIA labels to buttons
  - [ ] aria-label="Pause deliberation"
  - [ ] aria-label="Resume deliberation"
- [ ] Add keyboard navigation
  - [ ] Tab through form fields
  - [ ] Enter to submit
  - [ ] Escape to close modals
- [ ] Add focus indicators
  - [ ] Visible outline on focused elements
  - [ ] Skip navigation links

#### Dark Mode

- [ ] Add dark mode toggle (optional for MVP)
  - [ ] Use `prefers-color-scheme` media query
  - [ ] Store preference in localStorage
  - [ ] Update Tailwind config for dark mode

#### Code Quality

- [ ] Run ESLint
  ```bash
  npm run lint
  ```
- [ ] Run Prettier
  ```bash
  npm run format
  ```
- [ ] Fix all issues

#### Documentation

- [ ] Create `frontend/README.md`
  - [ ] How to run dev server
  - [ ] How to build for production
  - [ ] Component documentation
  - [ ] State management overview

**Validation**:
- [ ] Responsive on all screen sizes
- [ ] Accessible (keyboard navigation, ARIA)
- [ ] Dark mode works (optional)
- [ ] All lint/format checks pass

**Tests**:
Manual testing on multiple devices

**Go/No-Go for Week 8**:
- [ ] ✅ UI responsive (mobile, tablet, desktop)
- [ ] ✅ UI accessible (ARIA, keyboard)
- [ ] ✅ Real-time streaming works (SSE)
- [ ] ✅ Control actions work (pause, resume, kill)

---

## Week 8 (Days 50-56): Payments + Rate Limiting + GDPR

**Goal**: Stripe subscriptions, rate limiting, and GDPR compliance working

**Status**: 0/98 tasks complete

### Day 50-51: GDPR User Rights Implementation

**Goal**: Implement data export, account deletion, and data retention policies

**Tasks**:

#### Data Export Endpoint (GDPR Art. 15)
- [ ] Create endpoint: GET /api/v1/user/export
- [ ] Export user data as JSON:
  ```json
  {
    "profile": {"id": "...", "email": "...", "created_at": "..."},
    "sessions": [...],
    "contributions": [...],
    "votes": [...],
    "audit_logs": [...]
  }
  ```
- [ ] Test: Verify complete data export

#### Account Deletion Endpoint (GDPR Art. 17)
- [ ] Create endpoint: DELETE /api/v1/user/delete
- [ ] Implement anonymization (NOT hard delete):
  ```python
  # Anonymize user
  user.email = f"deleted_{user.id}@anonymized.local"
  user.anonymized_at = datetime.now()

  # Anonymize problem statements
  for session in user.sessions:
      session.problem_statement = "[REDACTED]"

  # Anonymize contributions (keep structure for analytics)
  for contribution in user.contributions:
      contribution.content = "[REDACTED]"
  ```
- [ ] Keep aggregate analytics (anonymized)
- [ ] Log deletion request (audit trail)
- [ ] Send confirmation email (optional, if user still has access)
- [ ] Test: Verify GDPR compliance

#### Data Retention Policy
- [ ] Default retention: 365 days (configurable by user)
- [ ] User setting: Configure retention period (365d, 730d, indefinite)
- [ ] Cleanup job: Archive sessions >365 days old
- [ ] Document retention policy in privacy policy

**Validation**:
- [ ] Data export includes all user data
- [ ] Account deletion anonymizes (not deletes)
- [ ] Anonymized data is truly unrecoverable
- [ ] Audit log records deletion request

**Tests**:
```bash
pytest tests/test_gdpr_compliance.py -v

# Test data export
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/user/export

# Test account deletion
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/user/delete
```

**Deliverables**:
- backend/api/routes/gdpr.py
- tests/test_gdpr_compliance.py
- docs/GDPR_COMPLIANCE.md

---

### Day 52: Stripe Integration Setup

**Value**: Accept payments for subscriptions

#### Stripe Account Setup

- [ ] Create Stripe account at stripe.com
  - [ ] Organization: Board of One
  - [ ] Enable test mode
  - [ ] Add bank account (for payouts later)
- [ ] Create products
  - [ ] Free tier (no product needed)
  - [ ] Pro tier ($29/month recurring)
    - [ ] Name: "Board of One Pro"
    - [ ] Price: $29 USD/month
    - [ ] Save price ID to env vars
  - [ ] Enterprise tier (custom pricing)
    - [ ] Name: "Board of One Enterprise"
    - [ ] Price: Contact sales

#### Environment Configuration

- [ ] Add Stripe keys to `.env`
  ```bash
  STRIPE_SECRET_KEY=sk_test_xxx
  STRIPE_PUBLISHABLE_KEY=pk_test_xxx
  STRIPE_WEBHOOK_SECRET=whsec_xxx
  STRIPE_PRO_PRICE_ID=price_xxx
  ```
- [ ] Add to frontend `.env`
  ```bash
  VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
  ```

#### Stripe Client (Backend)

- [ ] Install Stripe SDK
  ```bash
  uv add stripe
  ```
- [ ] Create `backend/integrations/stripe.py`
  - [ ] Initialize Stripe client
  - [ ] `create_customer()` - Create Stripe customer on signup
  - [ ] `create_checkout_session()` - Start subscription flow
  - [ ] `get_subscription()` - Check subscription status

#### Database Update

- [ ] Add Stripe fields to `users` table
  ```sql
  ALTER TABLE users ADD COLUMN stripe_customer_id TEXT UNIQUE;
  ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT;
  ALTER TABLE users ADD COLUMN subscription_status TEXT;  -- active, canceled, past_due
  ```

#### Testing

- [ ] Test: Stripe client works
  ```python
  customer = create_customer(user.email)
  assert customer.id.startswith('cus_')
  ```
- [ ] Test: Can create checkout session
  ```python
  session = create_checkout_session(customer.id, 'pro')
  assert session.url is not None
  ```

**Validation**:
- [ ] Stripe account created
- [ ] Products created (Pro tier)
- [ ] Stripe client works (test mode)
- [ ] Database updated with Stripe fields

**Tests**:
```bash
pytest backend/tests/test_stripe_integration.py -v
```

#### Rate Limiting Implementation
- [ ] Install rate limiting library: `uv add slowapi redis`
- [ ] Create rate limiter service (backend/services/rate_limiter.py)
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address

  limiter = Limiter(key_func=get_remote_address)

  TIER_LIMITS = {
      "free": "10/minute",
      "pro": "30/minute",
      "enterprise": "100/minute"
  }
  ```
- [ ] Add middleware to check user tier and apply limits
- [ ] Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
- [ ] Redis backend for distributed rate limiting
- [ ] Create rate limit exceeded endpoint (429 response)
- [ ] Add rate limiting to all API endpoints:
  - [ ] POST /api/v1/sessions (create deliberation)
  - [ ] GET /api/v1/sessions (list sessions)
  - [ ] POST /api/v1/sessions/{id}/resume (resume session)

**Validation**:
- [ ] Free tier limited to 10 requests/minute
- [ ] Pro tier limited to 30 requests/minute
- [ ] Enterprise tier limited to 100 requests/minute
- [ ] 429 status returned when limit exceeded
- [ ] Rate limit headers present in response

**Tests**:
```bash
pytest tests/test_rate_limiting.py -v

# Manual test: Exceed free tier limit
for i in {1..15}; do curl http://localhost:8000/api/v1/sessions; done
# Expect: First 10 succeed (200), next 5 fail (429)
```

---

### Day 53: Checkout Flow Implementation

**Value**: Users can upgrade to Pro

#### Pricing Page

- [ ] Create `src/routes/(app)/pricing/+page.svelte`
  - [ ] Display pricing tiers:
    - [ ] Free: $0/month (5 sessions, basic personas)
    - [ ] Pro: $29/month (50 sessions, all personas, PDF export)
    - [ ] Enterprise: Custom (unlimited, API access, SLA)
  - [ ] "Upgrade to Pro" button
  - [ ] Feature comparison table

#### Checkout Endpoint

- [ ] Create `backend/api/checkout.py`
  - [ ] `POST /api/v1/checkout` - Create Stripe Checkout session
    - [ ] Require auth
    - [ ] Get user's Stripe customer ID (create if not exists)
    - [ ] Create checkout session for Pro price
    - [ ] Return checkout URL
- [ ] Frontend: Redirect to Stripe Checkout
  ```typescript
  async function upgradeToPro() {
      const { url } = await apiClient.createCheckoutSession('pro');
      window.location.href = url;  // Redirect to Stripe
  }
  ```

#### Success/Cancel Handlers

- [ ] Create `src/routes/(app)/billing/success/+page.svelte`
  - [ ] Thank you message
  - [ ] "Return to dashboard" button
- [ ] Create `src/routes/(app)/billing/cancel/+page.svelte`
  - [ ] "Checkout canceled" message
  - [ ] "Try again" button

#### Testing

- [ ] Test: Pricing page displays
  - [ ] Visit /pricing
  - [ ] Verify tiers displayed
- [ ] Test: Checkout flow works
  - [ ] Click "Upgrade to Pro"
  - [ ] Verify redirected to Stripe Checkout
  - [ ] Complete checkout (test card: 4242 4242 4242 4242)
  - [ ] Verify redirected to /billing/success
- [ ] Test: Cancel flow works
  - [ ] Start checkout, click "Back"
  - [ ] Verify redirected to /billing/cancel

**Validation**:
- [ ] Pricing page displays correctly
- [ ] Checkout flow works (test mode)
- [ ] Success/cancel pages work
- [ ] Test card payment succeeds

**Tests**:
Manual testing with Stripe test cards

---

### Day 54: Stripe Webhooks + Subscription Management

**Value**: Subscription updates sync to database

#### Webhook Endpoint

- [ ] Create `backend/api/webhooks/stripe.py`
  - [ ] `POST /api/webhooks/stripe` - Handle Stripe events
    - [ ] Verify webhook signature (security)
    - [ ] Handle events:
      - [ ] `customer.subscription.created` → Update user (tier=pro)
      - [ ] `customer.subscription.updated` → Update subscription status
      - [ ] `customer.subscription.deleted` → Downgrade to free
      - [ ] `invoice.paid` → Send payment receipt email (Day 55)
    - [ ] Return 200 OK (acknowledge receipt)

#### Subscription Update Logic

- [ ] Create `update_user_subscription()` function
  ```python
  async def update_user_subscription(subscription):
      tier = 'pro' if subscription.items.data[0].price.id == PRO_PRICE_ID else 'free'
      await db.execute("""
          UPDATE users SET
              subscription_tier = $1,
              stripe_subscription_id = $2,
              subscription_status = $3
          WHERE stripe_customer_id = $4
      """, [tier, subscription.id, subscription.status, subscription.customer])
  ```

#### Stripe Customer Portal

- [ ] Add `POST /api/v1/billing/portal` endpoint
  - [ ] Create Stripe billing portal session
  - [ ] Return portal URL
  - [ ] User can cancel subscription here
- [ ] Add "Manage Billing" button to dashboard
  - [ ] Click → Redirect to Stripe portal
  - [ ] User can view invoices, cancel subscription

#### Testing

- [ ] Test: Webhook signature validation
  - [ ] Send webhook with invalid signature
  - [ ] Verify 400 error
  - [ ] Send webhook with valid signature
  - [ ] Verify 200 OK
- [ ] Test: Subscription created webhook
  - [ ] Trigger `customer.subscription.created` event (Stripe CLI)
  - [ ] Verify user tier updated to 'pro'
- [ ] Test: Subscription deleted webhook
  - [ ] Trigger `customer.subscription.deleted` event
  - [ ] Verify user tier downgraded to 'free'
- [ ] Test: Customer portal works
  - [ ] Click "Manage Billing"
  - [ ] Verify redirected to Stripe portal
  - [ ] Cancel subscription
  - [ ] Verify webhook received

**Validation**:
- [ ] Webhook endpoint works (signature verified)
- [ ] Subscription events update database
- [ ] Customer portal works (user can cancel)
- [ ] Downgrade to free works

**Tests**:
```bash
pytest backend/tests/test_stripe_webhooks.py -v
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

---

### Day 55: Resend Email Integration

**Value**: Send transactional emails (welcome, receipts)

#### Resend Account Setup

- [ ] Create Resend account at resend.com
  - [ ] Verify domain (boardofone.com)
  - [ ] Add DNS records:
    - [ ] TXT: resend._domainkey (DKIM)
    - [ ] TXT: SPF record
    - [ ] TXT: DMARC record
  - [ ] Get API key

#### Environment Configuration

- [ ] Add Resend variables to `.env`
  ```bash
  RESEND_API_KEY=re_xxx
  RESEND_FROM_EMAIL=noreply@boardofone.com
  RESEND_FROM_NAME="Board of One"
  RESEND_REPLY_TO=support@boardofone.com
  ```

#### Email Service

- [ ] Install Resend SDK
  ```bash
  uv add resend
  ```
- [ ] Create `backend/services/email.py`
  - [ ] `EmailService` class
    - [ ] `send_email()` - Send via Resend
    - [ ] Retry logic (exponential backoff)
    - [ ] Error handling
  - [ ] Pre-defined methods:
    - [ ] `send_welcome_email(user_email)`
    - [ ] `send_payment_receipt(user_email, amount)`

#### Email Templates

- [ ] Create `backend/services/email_templates.py`
  - [ ] `render_welcome_email()` - HTML template
    - [ ] Welcome message
    - [ ] Getting started tips
    - [ ] Link to first deliberation
  - [ ] `render_payment_receipt()` - HTML template
    - [ ] Thank you message
    - [ ] Invoice details (amount, date)
    - [ ] Link to billing portal

#### Testing

- [ ] Test: Resend API works
  ```python
  email_service = EmailService()
  response = email_service.send_email(
      to='test@example.com',
      subject='Test',
      html='<p>Hello</p>'
  )
  assert response['id'] is not None
  ```
- [ ] Test: Welcome email sends
  ```python
  await email_service.send_welcome_email('user@example.com')
  # Check inbox for email
  ```
- [ ] Test: Payment receipt sends
  ```python
  await email_service.send_payment_receipt('user@example.com', 29.00)
  # Check inbox for email
  ```

**Validation**:
- [ ] Resend account created
- [ ] Domain verified (DKIM, SPF, DMARC)
- [ ] Email service works
- [ ] Templates render correctly
- [ ] Emails delivered to inbox (not spam)

**Tests**:
```bash
pytest backend/tests/test_email_service.py -v
```

---

### Day 56: Email Triggers + Pre-commit

**Value**: Emails sent automatically on key events

#### Supabase Auth Webhook (Welcome Email)

- [ ] Create `backend/api/webhooks/supabase.py`
  - [ ] `POST /api/webhooks/supabase/auth` - Handle user signup
    - [ ] Event type: `user.created`
    - [ ] Send welcome email
    - [ ] Create user record in `users` table
    - [ ] Create Stripe customer
  - [ ] Configure webhook in Supabase dashboard
    - [ ] URL: `https://api.boardofone.com/api/webhooks/supabase/auth`
    - [ ] Events: `INSERT` on `auth.users`

#### Payment Receipt Email (Stripe Webhook)

- [ ] Update `backend/api/webhooks/stripe.py`
  - [ ] On `invoice.paid` event:
    - [ ] Send payment receipt email
    - [ ] Include: Amount, date, invoice PDF link
  - [ ] Testing:
    - [ ] Complete test checkout
    - [ ] Verify email received

#### Code Quality

- [ ] Run pre-commit checks
  ```bash
  make pre-commit
  ```
- [ ] Fix all issues
- [ ] Ensure test coverage >90%
  ```bash
  pytest --cov=backend --cov-report=html
  ```

#### Documentation

- [ ] Update `README.md`
  - [ ] Add: Payment flow documentation
  - [ ] Add: Email integration details
  - [ ] Add: How to test Stripe webhooks (Stripe CLI)
- [ ] Create `zzz_project/WEEK8_PAYMENTS_EMAIL_SUMMARY.md`
  - [ ] Stripe integration complete
  - [ ] Resend integration complete
  - [ ] Email triggers documented

**Validation**:
- [ ] Welcome email sends on signup
- [ ] Payment receipt sends on payment
- [ ] All pre-commit checks pass
- [ ] Documentation complete

**Tests**:
```bash
pytest backend/tests/test_email_triggers.py -v
```

**Go/No-Go for Week 9**:
- [ ] ✅ Stripe integration works (test mode)
- [ ] ✅ Resend emails deliver successfully
- [ ] ✅ Webhooks handle all events correctly
- [ ] ✅ All tests pass

---

---

## Week 9 (Days 57-63): Production Hardening + Monitoring

**Goal**: System is production-ready with monitoring, alerts, and guardrails

**Status**: 0/70 tasks complete

### Day 57: Runaway Session Detection

**Value**: Detect and alert on sessions consuming too many resources

#### Detection Metrics

- [ ] Create `backend/services/monitoring.py`
  - [ ] `RunawayDetector` class
    - [ ] `check_session_health()` - Called every 30 seconds
    - [ ] Metrics tracked:
      - [ ] Duration: Flag if >2x median (e.g., >30 min when median is 15 min)
      - [ ] Cost: Flag if >3x median (e.g., >$0.30 when median is $0.10)
      - [ ] Rounds: Flag if >max_rounds + 2 (safety margin)
    - [ ] Return: `is_runaway: bool`, `reason: str`, `severity: str`

#### Alert Triggers

- [ ] Create alert thresholds
  - [ ] **Warning** (notify admin, let continue):
    - [ ] Duration >1.5x median
    - [ ] Cost >2x median
    - [ ] Rounds >max_rounds
  - [ ] **Critical** (auto-kill):
    - [ ] Duration >3x median
    - [ ] Cost >5x median
    - [ ] Rounds >max_rounds + 5

#### Background Monitoring Task

- [ ] Create `backend/services/background_tasks.py`
  - [ ] `monitor_active_sessions()` - Runs every 30 seconds
    - [ ] Get all active sessions
    - [ ] Check each with `RunawayDetector`
    - [ ] If warning: Send alert (ntfy.sh)
    - [ ] If critical: Auto-kill + send alert
  - [ ] Start on API startup (`@app.on_event("startup")`)

#### Testing

- [ ] Test: Runaway detection works
  - [ ] Create session with artificially high cost
  - [ ] Wait 30 seconds
  - [ ] Verify warning triggered
- [ ] Test: Auto-kill works
  - [ ] Create session with cost >5x median
  - [ ] Verify auto-killed
  - [ ] Verify alert sent
- [ ] Test: False positives rare
  - [ ] Run 10 normal sessions
  - [ ] Verify no false alarms

**Validation**:
- [ ] Detection logic works (duration, cost, rounds)
- [ ] Alerts trigger at correct thresholds
- [ ] Auto-kill works (critical threshold)
- [ ] False positive rate <5%

**Tests**:
```bash
pytest backend/tests/test_runaway_detection.py -v
```

---

### Day 58: ntfy.sh Alert Integration

**Value**: Admin receives real-time alerts for critical events

#### ntfy.sh Setup

- [ ] Create ntfy.sh topic
  - [ ] Topic name: `bo1-prod-alerts` (keep secret)
  - [ ] Subscribe on admin phone (ntfy.sh app)
  - [ ] Test: Send test notification
- [ ] Add to `.env`
  ```bash
  NTFY_TOPIC=bo1-prod-alerts
  NTFY_URL=https://ntfy.sh
  NTFY_PRIORITY_WARNING=default
  NTFY_PRIORITY_CRITICAL=urgent
  ```

#### Alert Service

- [ ] Create `backend/services/alerts.py`
  - [ ] `AlertService` class
    - [ ] `send_alert()` - Send to ntfy.sh
      - [ ] message: str
      - [ ] priority: str (default, high, urgent)
      - [ ] tags: list[str] (for filtering)
    - [ ] Pre-defined methods:
      - [ ] `alert_runaway_session()`
      - [ ] `alert_system_error()`
      - [ ] `alert_cost_spike()`
      - [ ] `alert_api_down()`

#### Alert Templates

- [ ] Define alert formats
  - [ ] Runaway session:
    ```
    ⚠️ RUNAWAY SESSION
    Session: {session_id}
    User: {user_email}
    Duration: {duration}min (vs {median}min median)
    Cost: ${cost} (vs ${median} median)
    Action: Auto-killed
    ```
  - [ ] Cost spike:
    ```
    💰 COST SPIKE DETECTED
    Last hour: ${total_cost}
    vs Previous hour: ${prev_cost}
    Increase: +{percent}%
    Top session: {session_id} (${session_cost})
    ```
  - [ ] System error:
    ```
    🔥 SYSTEM ERROR
    Service: {service}
    Error: {error_message}
    Time: {timestamp}
    ```

#### Integration

- [ ] Update `RunawayDetector`
  - [ ] On warning: `alert_service.alert_runaway_session(session, 'warning')`
  - [ ] On critical: `alert_service.alert_runaway_session(session, 'critical')`
- [ ] Update error handlers
  - [ ] On uncaught exception: `alert_service.alert_system_error()`

#### Testing

- [ ] Test: ntfy.sh receives alerts
  - [ ] Trigger runaway detection
  - [ ] Check phone for notification
  - [ ] Verify message format correct
- [ ] Test: Priority levels work
  - [ ] Send `default` priority (no sound)
  - [ ] Send `urgent` priority (loud alarm)
- [ ] Test: Alert rate limiting
  - [ ] Trigger 10 warnings in 1 minute
  - [ ] Verify only 1 alert sent (deduplicated)

**Validation**:
- [ ] ntfy.sh integration works
- [ ] Alerts received on admin phone
- [ ] Priority levels work correctly
- [ ] Alert deduplication works (rate limiting)

**Tests**:
```bash
pytest backend/tests/test_alerts.py -v
```

---

### Day 59: Cost Analytics Dashboard (Admin)

**Value**: Admin visibility into spending patterns

#### Cost Aggregation

- [ ] Create `backend/services/analytics.py`
  - [ ] `CostAnalytics` class
    - [ ] `get_cost_summary()` - Last 24h, 7d, 30d
      - [ ] Total cost
      - [ ] Session count
      - [ ] Average cost per session
      - [ ] Cost by tier (free, pro, enterprise)
      - [ ] Cost by phase (decomposition, deliberation, synthesis)
    - [ ] `get_cost_trend()` - Hourly for last 24h
      - [ ] Array of {hour, cost, sessions}
      - [ ] Calculate trend (increasing, stable, decreasing)
    - [ ] `get_top_sessions()` - Most expensive sessions
      - [ ] Top 10 by cost
      - [ ] Include: user, duration, rounds, cost breakdown

#### Admin Endpoint

- [ ] Add `GET /api/admin/analytics/cost`
  - [ ] Query params: period (24h, 7d, 30d)
  - [ ] Return: CostSummary (JSON)
- [ ] Add `GET /api/admin/analytics/cost/trend`
  - [ ] Return: Array of hourly costs (last 24h)
- [ ] Add `GET /api/admin/analytics/sessions/expensive`
  - [ ] Return: Top 10 most expensive sessions

#### Console Display (Admin CLI)

- [ ] Create `scripts/admin_cost_report.py`
  - [ ] Fetch cost analytics from API
  - [ ] Display Rich tables:
    - [ ] Cost summary (24h, 7d, 30d)
    - [ ] Cost trend (line chart, Rich rendering)
    - [ ] Top 10 expensive sessions
  - [ ] Run via: `python scripts/admin_cost_report.py`

#### Testing

- [ ] Test: Cost summary correct
  - [ ] Run 10 sessions with known costs
  - [ ] Fetch summary
  - [ ] Verify totals match
- [ ] Test: Cost trend works
  - [ ] Run sessions over 3 hours
  - [ ] Fetch trend
  - [ ] Verify hourly breakdown correct
- [ ] Test: Top sessions accurate
  - [ ] Run sessions with varying costs
  - [ ] Fetch top 10
  - [ ] Verify sorted by cost descending

**Validation**:
- [ ] Cost analytics accurate
- [ ] Trend calculation works
- [ ] Top sessions ranked correctly
- [ ] Console display readable

**Tests**:
```bash
pytest backend/tests/test_cost_analytics.py -v
python scripts/admin_cost_report.py
```

---

### Day 60: Rate Limiting (Per-Tier)

**Value**: Prevent abuse, enforce subscription limits

#### Rate Limit Configuration

- [ ] Define tier limits in `backend/config.py`
  ```python
  TIER_LIMITS = {
      'free': {
          'sessions_per_month': 5,
          'sessions_per_day': 2,
          'concurrent_sessions': 1,
          'max_rounds_per_session': 7,
      },
      'pro': {
          'sessions_per_month': 50,
          'sessions_per_day': 10,
          'concurrent_sessions': 3,
          'max_rounds_per_session': 15,
      },
      'enterprise': {
          'sessions_per_month': -1,  # Unlimited
          'sessions_per_day': -1,
          'concurrent_sessions': 10,
          'max_rounds_per_session': 15,
      }
  }
  ```

#### Rate Limiter

- [ ] Create `backend/middleware/rate_limit.py`
  - [ ] `RateLimiter` class
    - [ ] Redis-backed counters (sliding window)
    - [ ] `check_limit()` - Returns remaining quota
    - [ ] `increment()` - Increment counter
    - [ ] `reset()` - Reset on tier upgrade
  - [ ] Middleware: `check_rate_limit()`
    - [ ] Extract user tier from session
    - [ ] Check limit for endpoint
    - [ ] If exceeded: Return 429 with Retry-After header
    - [ ] If allowed: Increment counter, continue

#### Apply to Endpoints

- [ ] Add middleware to session creation
  ```python
  @app.post("/api/v1/sessions")
  async def create_session(
      request: Request,
      user = Depends(require_auth)
  ):
      await check_rate_limit(user, 'sessions_per_day')
      # ... create session
  ```
- [ ] Add to deliberation start
  - [ ] Check `concurrent_sessions` limit
  - [ ] Block if user already at limit

#### User-Facing Errors

- [ ] Return helpful error messages
  ```json
  {
      "error": "Rate limit exceeded",
      "message": "You've reached your daily limit (2 sessions). Upgrade to Pro for 10 sessions/day.",
      "limit": 2,
      "remaining": 0,
      "reset_at": "2025-11-16T00:00:00Z",
      "upgrade_url": "/pricing"
  }
  ```

#### Testing

- [ ] Test: Free tier enforced (5 sessions/month)
  - [ ] Create 5 sessions
  - [ ] Attempt 6th
  - [ ] Verify 429 error
- [ ] Test: Pro tier enforced (50 sessions/month)
  - [ ] Create 50 sessions (test user)
  - [ ] Attempt 51st
  - [ ] Verify 429 error
- [ ] Test: Concurrent sessions enforced
  - [ ] Start 2 sessions (free tier, limit=1)
  - [ ] Verify 2nd blocked
- [ ] Test: Rate limit reset works
  - [ ] Hit limit, wait until reset time
  - [ ] Verify counter reset

**Validation**:
- [ ] Rate limits enforced per tier
- [ ] Redis counters work (sliding window)
- [ ] Error messages helpful
- [ ] Upgrade prompts shown

**Tests**:
```bash
pytest backend/tests/test_rate_limiting.py -v
```

---

### Day 61: Health Checks + Graceful Shutdown

**Value**: Production reliability (readiness probes, zero-downtime deploys)

#### Advanced Health Checks

- [ ] Update `backend/api/health.py`
  - [ ] `GET /api/health/ready` - Readiness probe
    - [ ] Check: Redis responding (<100ms)
    - [ ] Check: PostgreSQL responding (<100ms)
    - [ ] Check: Anthropic API reachable (cache last check, 5 min TTL)
    - [ ] Return: 200 if all healthy, 503 if any unhealthy
  - [ ] `GET /api/health/live` - Liveness probe
    - [ ] Basic health check (app is running)
    - [ ] Always 200 (unless crash)
  - [ ] `GET /api/health/startup` - Startup probe
    - [ ] Check: Redis connection established
    - [ ] Check: Database migrations applied
    - [ ] Return: 200 once fully started

#### Graceful Shutdown

- [ ] Update `backend/api/main.py`
  - [ ] Register signal handlers (SIGTERM, SIGINT)
  - [ ] On shutdown:
    - [ ] Stop accepting new requests (readiness = false)
    - [ ] Wait for active sessions to complete (30s grace period)
    - [ ] Cancel remaining sessions (save checkpoints)
    - [ ] Close database connections
    - [ ] Close Redis connections
    - [ ] Exit cleanly
  ```python
  @app.on_event("shutdown")
  async def shutdown_event():
      logger.info("Shutdown initiated, stopping new requests")
      # ... graceful shutdown logic
  ```

#### Deployment Configuration

- [ ] Create `k8s/deployment.yaml` (for DigitalOcean Kubernetes)
  - [ ] Readiness probe: `/api/health/ready` (10s interval)
  - [ ] Liveness probe: `/api/health/live` (30s interval)
  - [ ] Startup probe: `/api/health/startup` (5s interval, 60s timeout)
  - [ ] Graceful termination: `terminationGracePeriodSeconds: 30`

#### Testing

- [ ] Test: Readiness probe fails when Redis down
  - [ ] Stop Redis
  - [ ] GET /api/health/ready
  - [ ] Verify 503 response
- [ ] Test: Liveness probe always succeeds
  - [ ] GET /api/health/live
  - [ ] Verify 200 (even if Redis down)
- [ ] Test: Graceful shutdown works
  - [ ] Start 2 active sessions
  - [ ] Send SIGTERM
  - [ ] Verify sessions complete or checkpoint saved
  - [ ] Verify app exits cleanly (no errors)

**Validation**:
- [ ] Health checks work (ready, live, startup)
- [ ] Graceful shutdown works (no data loss)
- [ ] Kubernetes probes configured
- [ ] Zero-downtime deploys possible

**Tests**:
```bash
pytest backend/tests/test_health_checks.py -v
pytest backend/tests/test_graceful_shutdown.py -v
```

**Deliverables**:
- backend/api/health.py (updated with all probes)
- k8s/deployment.yaml
- docs/GRACEFUL_SHUTDOWN.md

#### Vendor Outage Contingency Plans

**Value**: System resilience when third-party services fail

**Tasks**:
- [ ] Document degraded mode operation (what works when vendors down?)
  - Supabase down: Cannot auth, existing sessions work (JWT cached)
  - Anthropic down: Cannot create deliberations, can view history
  - Stripe down: Cannot upgrade, existing Pro users unaffected
  - Resend down: Emails queued, retry after 1 hour
- [ ] Create vendor status monitoring
  ```python
  # Check vendor health every 5 minutes
  async def check_vendor_health():
      statuses = {
          "supabase": await check_supabase(),
          "anthropic": await check_anthropic(),
          "stripe": await check_stripe(),
          "resend": await check_resend()
      }
      if any(not v for v in statuses.values()):
          await notify_admin(f"Vendor down: {statuses}")
  ```
- [ ] Integrate status page APIs
  - Supabase: https://status.supabase.com (RSS feed)
  - Stripe: https://status.stripe.com (API)
  - Monitor every 5 minutes, alert on incidents
- [ ] Create fallback strategies
  - Anthropic down → Queue deliberations, retry when back up
  - Stripe down → Show "payment processing unavailable" banner
- [ ] Test degraded mode (disable each vendor, verify UX)

**Validation**:
- [ ] Status monitoring detects vendor outages within 5 minutes
- [ ] Degraded mode UX tested for all 4 vendors
- [ ] Admin receives alerts when vendor down

**Tests**:
```bash
# Test vendor health checks
pytest tests/test_vendor_health.py -v

# Simulate vendor outage
MOCK_ANTHROPIC_DOWN=true pytest tests/test_degraded_mode.py -v
```

**Deliverables**:
- backend/services/vendor_health.py
- docs/VENDOR_CONTINGENCY_PLANS.md

#### Cost Anomaly Detection & Budget Controls

**Value**: Prevent unexpected cost spikes

**Tasks**:
- [ ] Implement per-user cost tracking (real-time)
  ```python
  # Track cost per LLM call
  async def track_cost(user_id: str, cost: float, phase: str):
      redis.zincrby(f"user_cost:{user_id}:daily", cost, datetime.now().date())
      redis.zincrby(f"user_cost:{user_id}:monthly", cost, datetime.now().month)
  ```
- [ ] Set budget thresholds per tier
  ```python
  BUDGET_LIMITS = {
      "free": {"daily": 0.10, "monthly": 1.00},
      "pro": {"daily": 5.00, "monthly": 50.00},
      "enterprise": {"daily": 50.00, "monthly": 500.00}
  }
  ```
- [ ] Create cost anomaly detection
  ```python
  # Alert if user exceeds 3x average daily cost
  avg_cost = await get_user_avg_daily_cost(user_id)
  if today_cost > 3 * avg_cost:
      await notify_admin(f"Cost spike: {user_id} spent ${today_cost:.2f}")
  ```
- [ ] Implement auto-pause on budget exceeded
  ```python
  # Gracefully pause deliberation if budget exceeded
  if user_cost_today >= tier_daily_limit:
      await pause_session(session_id)
      await notify_user("Daily budget reached, deliberation paused")
  ```
- [ ] Admin dashboard: Cost per user (sortable, filterable)
- [ ] Test: Exceed budget, verify auto-pause

**Validation**:
- [ ] Cost tracked per LLM call (Anthropic + Voyage)
- [ ] Admin receives alert when user exceeds 3x average
- [ ] Deliberation auto-pauses when budget exceeded
- [ ] User notified gracefully (not error)

**Tests**:
```bash
pytest tests/test_cost_tracking.py -v
pytest tests/test_budget_controls.py -v

# Simulate cost spike
MOCK_HIGH_COST=true pytest tests/test_anomaly_detection.py -v
```

**Deliverables**:
- backend/services/cost_tracker.py
- backend/middleware/budget_guard.py
- docs/COST_MANAGEMENT.md

#### Feature Flags for Gradual Rollout

**Value**: Deploy risky features safely with instant rollback

**Tasks**:
- [ ] Install feature flag library: `uv add launchdarkly-server-sdk` (or use simple Redis-based)
- [ ] Create simple feature flag service (backend/services/feature_flags.py)
  ```python
  class FeatureFlags:
      """Simple Redis-based feature flags."""

      async def is_enabled(self, flag: str, user_id: str = None) -> bool:
          # Check global flag
          global_enabled = await redis.get(f"flag:{flag}:enabled")
          if global_enabled == "false":
              return False

          # Check percentage rollout
          rollout_pct = await redis.get(f"flag:{flag}:rollout_pct")
          if rollout_pct:
              user_hash = hash(user_id) % 100
              if user_hash >= int(rollout_pct):
                  return False

          return True
  ```
- [ ] Implement feature flags for risky features:
  - `enable_parallel_subproblems` (future feature)
  - `enable_time_travel` (future feature)
  - `enable_human_in_loop` (future feature)
- [ ] Admin UI: Toggle feature flags (on/off/percentage rollout)
- [ ] Wrap risky code paths with flags
  ```python
  if await feature_flags.is_enabled("enable_time_travel", user_id):
      return await handle_time_travel_request()
  else:
      return {"error": "Feature not available yet"}
  ```
- [ ] Test: Verify flags work (on/off/percentage)

**Validation**:
- [ ] Feature flags can be toggled without deploy
- [ ] Percentage rollout works (50% = half users see feature)
- [ ] Admin UI shows flag status

**Tests**:
```bash
pytest tests/test_feature_flags.py -v

# Test rollout percentages
pytest tests/test_percentage_rollout.py -v
```

**Deliverables**:
- backend/services/feature_flags.py
- backend/api/routes/admin/feature_flags.py
- docs/FEATURE_FLAGS.md

#### Service Level Indicators & Objectives

**Value**: Define and measure service quality promises

**Tasks**:
- [ ] Define SLIs (what to measure)
  ```yaml
  sli:
    availability:
      metric: uptime_percentage
      calculation: (successful_requests / total_requests) * 100

    latency:
      metric: p95_response_time
      calculation: 95th percentile of all request durations

    error_rate:
      metric: error_percentage
      calculation: (5xx_responses / total_requests) * 100
  ```
- [ ] Set SLOs (targets)
  ```yaml
  slo:
    availability: 99.9%  # 43.2 minutes downtime/month allowed
    latency_p95: 2000ms  # 95% of requests under 2 seconds
    error_rate: 1%       # Less than 1% 5xx errors
  ```
- [ ] Document SLAs (user promises)
  ```markdown
  # Service Level Agreement (Public)

  Board of One commits to:
  - 99.9% uptime (monthly)
  - P95 latency <2s for deliberation API
  - <1% error rate

  If we miss SLA:
  - Pro users: 10% credit for that month
  - Enterprise: Custom compensation per contract
  ```
- [ ] Create SLO monitoring dashboard (Grafana)
  - Availability gauge (target: 99.9%)
  - Latency P95 graph (target: 2s line)
  - Error rate gauge (target: 1%)
- [ ] Alerting rules for SLO breaches
  ```yaml
  alerts:
    - name: SLO_Availability_Breach
      condition: availability < 99.9% over 1 hour
      severity: critical
      action: Page on-call engineer

    - name: SLO_Latency_Breach
      condition: p95_latency > 2000ms over 15 minutes
      severity: warning
      action: Slack notification

    - name: SLO_ErrorRate_Breach
      condition: error_rate > 1% over 5 minutes
      severity: critical
      action: Page on-call engineer
  ```
- [ ] Create error budget tracking
  ```python
  # Calculate remaining error budget
  monthly_error_budget = 0.1% # (100% - 99.9%)
  errors_consumed = current_error_rate * days_elapsed / 30
  budget_remaining = monthly_error_budget - errors_consumed

  if budget_remaining < 0.05%:
      # Freeze risky deploys, focus on stability
      await notify_team("Error budget low: freeze non-critical deploys")
  ```

**Validation**:
- [ ] SLIs measured and displayed in Grafana
- [ ] SLO dashboard shows current vs target
- [ ] Alerts fire when SLOs breached
- [ ] Error budget calculated correctly

**Deliverables**:
- docs/SLI_SLO_SLA.md
- grafana-dashboards/slo-dashboard.json
- prometheus/slo-alerts.yml

---

### Day 62: Logging + Structured Logs

**Value**: Production debugging (searchable, filterable logs)

#### Structured Logging

- [ ] Create `backend/utils/logger.py`
  - [ ] Configure `structlog` (Python)
    - [ ] JSON output (for log aggregation)
    - [ ] Log level: INFO (prod), DEBUG (dev)
    - [ ] Include: timestamp, level, message, context
  - [ ] Context processors:
    - [ ] `add_request_id()` - Add trace ID to all logs
    - [ ] `add_user_context()` - Add user_id if authenticated
    - [ ] `add_session_context()` - Add session_id if present
  - [ ] Example log:
    ```json
    {
        "timestamp": "2025-11-15T10:30:00Z",
        "level": "info",
        "message": "Deliberation started",
        "request_id": "abc123",
        "user_id": "usr_xyz",
        "session_id": "sess_789",
        "phase": "decomposition"
    }
    ```

#### Request Logging Middleware

- [ ] Create `backend/middleware/logging.py`
  - [ ] Log all incoming requests
    - [ ] Method, path, user, duration
  - [ ] Log all responses
    - [ ] Status code, duration, error (if any)
  - [ ] Skip: Health check endpoints (reduce noise)

#### Error Logging

- [ ] Update error handlers
  - [ ] Log all errors with full stack trace
  - [ ] Include: request_id, user_id, session_id
  - [ ] Send to Sentry (if configured)
- [ ] Add to all `except` blocks
  ```python
  except Exception as e:
      logger.error("Deliberation failed", exc_info=e, session_id=session.id)
      raise
  ```

#### Log Aggregation (Future)

- [ ] Document log aggregation setup (for production)
  - [ ] Option 1: Grafana Loki (open source)
  - [ ] Option 2: AWS CloudWatch Logs
  - [ ] Option 3: Datadog
  - [ ] Not implemented in MVP, but logs are structured for easy integration

#### Testing

- [ ] Test: Structured logs output JSON
  - [ ] Make API request
  - [ ] Check logs (stdout)
  - [ ] Verify JSON format
- [ ] Test: Context propagates correctly
  - [ ] Make authenticated request
  - [ ] Verify user_id in all logs for that request
- [ ] Test: Errors logged with stack traces
  - [ ] Trigger error
  - [ ] Verify stack trace in logs

**Validation**:
- [ ] Structured logs work (JSON output)
- [ ] Context propagates (request_id, user_id, session_id)
- [ ] Errors logged with stack traces
- [ ] Logs ready for aggregation

**Tests**:
```bash
pytest backend/tests/test_logging.py -v
```

---

### Day 63-64: Production Monitoring & Observability

**Goal**: Implement comprehensive monitoring with Prometheus, Grafana, and structured logging

**Tasks**:

#### Prometheus Metrics Instrumentation
- [ ] Install: `uv add prometheus-fastapi-instrumentator`
- [ ] Instrument FastAPI app (backend/api/main.py)
  ```python
  from prometheus_fastapi_instrumentator import Instrumentator

  instrumentator = Instrumentator()
  instrumentator.instrument(app).expose(app, endpoint="/metrics")
  ```
- [ ] Add custom metrics:
  - [ ] deliberation_duration_seconds (histogram)
  - [ ] llm_call_duration_seconds (histogram)
  - [ ] llm_call_cost_usd (counter)
  - [ ] cache_hit_rate (gauge)
  - [ ] active_sessions_count (gauge)
  - [ ] session_completion_rate (gauge)
- [ ] Test: Verify metrics at http://localhost:8000/metrics

#### Grafana Dashboards
- [ ] Setup Grafana (Docker or cloud)
- [ ] Add Prometheus data source
- [ ] Create 4 dashboards:
  1. **Deliberation Dashboard**:
     - [ ] Session creation rate (per minute)
     - [ ] Active sessions (gauge)
     - [ ] Session completion rate (%)
     - [ ] Session duration (P50, P95, P99)
  2. **LLM Dashboard**:
     - [ ] LLM call rate (per minute)
     - [ ] LLM latency (P50, P95, P99)
     - [ ] LLM cost (USD per hour)
     - [ ] Cache hit rate (%)
  3. **Business Dashboard**:
     - [ ] Revenue (USD per day)
     - [ ] New signups (per day)
     - [ ] Churn rate (%)
     - [ ] Average revenue per user (ARPU)
  4. **Infrastructure Dashboard**:
     - [ ] Request rate (per second)
     - [ ] Error rate (%)
     - [ ] Latency (P50, P95, P99)
     - [ ] Database connections
     - [ ] Redis memory usage

#### Alerting Rules
- [ ] Configure Prometheus alerting rules:
  - [ ] Error rate >5% for 5 minutes → PagerDuty/ntfy.sh
  - [ ] P95 latency >2s for 5 minutes → Warning
  - [ ] Database connections >80% → Critical
  - [ ] Redis memory >80% → Warning
- [ ] Test: Trigger test alert

#### Structured Logging
- [ ] Configure structured JSON logging (backend/utils/logging.py)
  ```python
  import structlog

  structlog.configure(
      processors=[
          structlog.processors.add_log_level,
          structlog.processors.TimeStamper(fmt="iso"),
          structlog.processors.JSONRenderer()
      ]
  )

  logger = structlog.get_logger()
  logger.info("session_created", session_id="123", user_id="456")
  ```
- [ ] Add context fields: session_id, user_id, trace_id, request_id
- [ ] Log all API requests (middleware)
- [ ] Log all LLM calls (with cost)

#### Log Aggregation
- [ ] Setup Grafana Loki (or CloudWatch Logs if AWS)
- [ ] Configure log shipping (promtail or Docker log driver)
- [ ] Retention: 30 days
- [ ] Test: Query logs by session_id in Grafana

#### Audit Logging
- [ ] Middleware: Log all API requests
  ```python
  audit_log.create(
      user_id=user_id,
      action="create_session",
      resource_type="session",
      resource_id=session_id,
      ip_address=request.client.host,
      timestamp=datetime.now()
  )
  ```
- [ ] Log authentication events (login, logout, token refresh)
- [ ] Log admin actions (kill session, view user data)
- [ ] Log GDPR requests (export, delete)
- [ ] Retention: 7 years (compliance requirement)

#### Security Headers Implementation
- [ ] Add security headers middleware (backend/api/middleware/security.py)
  ```python
  from starlette.middleware.base import BaseHTTPMiddleware

  class SecurityHeadersMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request, call_next):
          response = await call_next(request)
          response.headers["Content-Security-Policy"] = "default-src 'self'"
          response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
          response.headers["X-Frame-Options"] = "DENY"
          response.headers["X-Content-Type-Options"] = "nosniff"
          response.headers["X-XSS-Protection"] = "1; mode=block"
          return response
  ```
- [ ] Apply middleware to FastAPI app
- [ ] Test: Verify headers present
  ```bash
  curl -I http://localhost:8000 | grep -E "Content-Security-Policy|Strict-Transport-Security"
  ```

**Validation**:
- [ ] Prometheus scraping metrics successfully
- [ ] Grafana dashboards display real-time data
- [ ] Alerts fire when thresholds breached
- [ ] Logs queryable in Grafana Loki
- [ ] Audit logs contain all required fields
- [ ] All 5 security headers present in responses

**Tests**:
```bash
# Test metrics endpoint
curl http://localhost:8000/metrics | grep deliberation_duration

# Test logging
pytest tests/test_logging.py -v

# Test audit logging
pytest tests/test_audit_log.py -v

# Trigger test alert
curl -X POST http://localhost:8000/admin/test-alert
```

**Deliverables**:
- backend/utils/logging.py (structured logging)
- prometheus.yml (Prometheus config)
- grafana-dashboards/ (4 JSON dashboard files)
- alerting-rules.yml (Prometheus alert rules)
- docs/MONITORING_SETUP.md

**Go/No-Go for Week 10**:
- [ ] ✅ Infinite loop prevention tested (100% confidence)
- [ ] ✅ Runaway detection works (alerts sent)
- [ ] ✅ Rate limiting enforced (per-tier)
- [ ] ✅ Health checks work (Kubernetes probes)
- [ ] ✅ Logging structured (ready for aggregation)
- [ ] ✅ Prometheus metrics exposed
- [ ] ✅ Grafana dashboards working
- [ ] ✅ Security headers implemented

---

## Week 10-11 (Days 64-77): Admin Dashboard

**Goal**: Web-based admin dashboard for monitoring and control

**Status**: 0/98 tasks complete

### Day 64: Admin Dashboard Setup (SvelteKit)

**Value**: Foundation for admin monitoring UI

#### Route Structure

- [ ] Create admin routes in frontend
  ```bash
  mkdir -p src/routes/(admin)
  mkdir -p src/routes/(admin)/admin/dashboard
  mkdir -p src/routes/(admin)/admin/sessions
  mkdir -p src/routes/(admin)/admin/analytics
  mkdir -p src/routes/(admin)/admin/users
  ```
- [ ] Route layout: `src/routes/(admin)/+layout.svelte`
  - [ ] Admin sidebar navigation
  - [ ] Admin header (logout, user info)
  - [ ] Auth check (redirect to login if not admin)

#### Admin Auth Middleware

- [ ] Create `src/lib/auth/admin.ts`
  - [ ] `requireAdmin()` - Server-side check
    - [ ] Verify user authenticated
    - [ ] Verify user has admin role (check `users.role` field)
    - [ ] Redirect to /login if not admin
  - [ ] Add `role` field to `users` table
    ```sql
    ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
    UPDATE users SET role = 'admin' WHERE email = 'admin@boardofone.com';
    ```

#### Admin API Client

- [ ] Create `src/lib/api/admin.ts`
  - [ ] `AdminApiClient` class
    - [ ] Extends base `ApiClient`
    - [ ] Add admin API key header (`X-Admin-Key`)
    - [ ] Methods:
      - [ ] `getActiveSessions()`
      - [ ] `getSessionDetails(id)`
      - [ ] `killSession(id)`
      - [ ] `killAllSessions()`
      - [ ] `getCostAnalytics(period)`

#### Testing

- [ ] Test: Admin routes require admin role
  - [ ] Try accessing /admin/dashboard (non-admin)
  - [ ] Verify redirect to /login
- [ ] Test: Admin API client works
  - [ ] Call `getActiveSessions()` with admin key
  - [ ] Verify 200 OK
  - [ ] Call without admin key
  - [ ] Verify 403 Forbidden

**Validation**:
- [ ] Admin routes created
- [ ] Admin auth works (role check)
- [ ] Admin API client works
- [ ] Non-admins blocked from admin pages

**Tests**:
Manual testing + Playwright E2E

---

### Day 65: Active Sessions Monitor

**Value**: Real-time visibility into running sessions

#### Active Sessions Page

- [ ] Create `src/routes/(admin)/admin/sessions/active/+page.svelte`
  - [ ] Load active sessions from API
  - [ ] Display in table (sortable)
  - [ ] Columns:
    - [ ] Session ID (truncated, tooltip full)
    - [ ] User email
    - [ ] Status (active, paused)
    - [ ] Phase (decomposition, deliberation, voting)
    - [ ] Duration (live timer)
    - [ ] Cost (live update)
    - [ ] Rounds (current/max)
    - [ ] Actions (view, kill)

#### Live Updates

- [ ] Poll API every 5 seconds
  ```typescript
  onMount(() => {
      const interval = setInterval(async () => {
          activeSessions = await adminApiClient.getActiveSessions();
      }, 5000);
      return () => clearInterval(interval);
  });
  ```
- [ ] Highlight new sessions (since last poll)
- [ ] Fade out completed sessions

#### Session Details Modal

- [ ] Create `SessionDetailsModal.svelte`
  - [ ] Show on click session row
  - [ ] Display:
    - [ ] Full session state (JSON viewer)
    - [ ] Contributions (chronological)
    - [ ] Cost breakdown (per phase)
    - [ ] Token usage (input, output, cache)
  - [ ] Actions:
    - [ ] Kill session (with confirmation)
    - [ ] View full logs (future)

#### Testing

- [ ] Test: Active sessions page loads
  - [ ] Start 3 sessions
  - [ ] Visit /admin/sessions/active
  - [ ] Verify 3 sessions displayed
- [ ] Test: Live updates work
  - [ ] Start new session
  - [ ] Verify appears within 5 seconds
- [ ] Test: Session details modal works
  - [ ] Click session row
  - [ ] Verify modal opens
  - [ ] Verify data displayed correctly

**Validation**:
- [ ] Active sessions page displays correctly
- [ ] Live updates work (5s polling)
- [ ] Session details modal works
- [ ] Kill session action works

**Tests**:
Manual testing + Playwright E2E

---

### Day 66: Cost Analytics Dashboard

**Value**: Visual cost insights for admin

#### Cost Overview Page

- [ ] Create `src/routes/(admin)/admin/analytics/cost/+page.svelte`
  - [ ] Display cost metrics:
    - [ ] Total cost (24h, 7d, 30d)
    - [ ] Session count (24h, 7d, 30d)
    - [ ] Average cost per session
    - [ ] Cost by tier (free, pro, enterprise)
    - [ ] Cost by phase (decomposition, deliberation, synthesis)

#### Charts

- [ ] Install charting library
  ```bash
  npm install chart.js svelte-chartjs
  ```
- [ ] Create charts:
  - [ ] Cost trend (line chart, last 24h)
  - [ ] Cost by tier (pie chart)
  - [ ] Cost by phase (bar chart)
  - [ ] Top 10 expensive sessions (table)

#### Export Functionality

- [ ] Add "Export CSV" button
  - [ ] Generate CSV from cost analytics
  - [ ] Include: date, session_id, user, cost, tier, phase
  - [ ] Download via browser

#### Testing

- [ ] Test: Cost analytics page loads
  - [ ] Visit /admin/analytics/cost
  - [ ] Verify metrics displayed
- [ ] Test: Charts render
  - [ ] Verify line chart (cost trend)
  - [ ] Verify pie chart (cost by tier)
  - [ ] Verify bar chart (cost by phase)
- [ ] Test: CSV export works
  - [ ] Click "Export CSV"
  - [ ] Verify file downloads
  - [ ] Verify data correct

**Validation**:
- [ ] Cost analytics page displays correctly
- [ ] Charts render correctly
- [ ] CSV export works
- [ ] Data accurate

**Tests**:
Manual testing

---

### Day 67: User Management

**Value**: Admin can view/manage users

#### Users Page

- [ ] Create `src/routes/(admin)/admin/users/+page.svelte`
  - [ ] Load all users from API
  - [ ] Display in table (sortable, filterable)
  - [ ] Columns:
    - [ ] Email
    - [ ] Tier (free, pro, enterprise)
    - [ ] Status (active, canceled)
    - [ ] Sessions count (total)
    - [ ] Total cost (all time)
    - [ ] Created at
    - [ ] Last login
    - [ ] Actions (view, impersonate, ban)

#### User Details

- [ ] Create `UserDetailsModal.svelte`
  - [ ] Display:
    - [ ] User info (email, tier, dates)
    - [ ] Session history (list)
    - [ ] Cost breakdown (by session)
    - [ ] Stripe customer ID (link to Stripe dashboard)
  - [ ] Actions:
    - [ ] Change tier (manual override)
    - [ ] Ban user (disable account)
    - [ ] Delete user (anonymize, GDPR)

#### User Search

- [ ] Add search input
  - [ ] Search by email
  - [ ] Debounced (500ms)
  - [ ] Update results live

#### Testing

- [ ] Test: Users page loads
  - [ ] Visit /admin/users
  - [ ] Verify users displayed
- [ ] Test: Search works
  - [ ] Type email
  - [ ] Verify filtered results
- [ ] Test: User details modal works
  - [ ] Click user row
  - [ ] Verify modal opens
  - [ ] Verify data correct

**Validation**:
- [ ] Users page displays correctly
- [ ] Search works (debounced)
- [ ] User details modal works
- [ ] Actions work (change tier, ban, delete)

**Tests**:
Manual testing + Playwright E2E

---

### Day 68: Kill Switches (Admin UI)

**Value**: Admin can terminate runaway sessions from UI

#### Kill Session Action

- [ ] Add "Kill" button to active sessions table
  - [ ] On click: Open confirmation modal
    - [ ] Show: Session details (user, duration, cost)
    - [ ] Input: Kill reason (required)
    - [ ] Warning: "This will terminate the session immediately"
  - [ ] On confirm:
    - [ ] Call `adminApiClient.killSession(id, reason)`
    - [ ] Show success toast
    - [ ] Remove from active sessions list

#### Kill All Sessions (Emergency)

- [ ] Add "Kill All Sessions" button (top-right, admin only)
  - [ ] Red color (danger)
  - [ ] Requires double confirmation
    - [ ] Modal 1: "Are you sure? This will kill ALL active sessions."
    - [ ] Modal 2: Type "KILL ALL" to confirm
  - [ ] On confirm:
    - [ ] Call `adminApiClient.killAllSessions()`
    - [ ] Show count of killed sessions
    - [ ] Refresh active sessions list

#### Audit Trail

- [ ] Display kill history
  - [ ] Create `/admin/sessions/killed` page
  - [ ] Show: session_id, user, killed_at, killed_by, reason
  - [ ] Filter by date range

#### Testing

- [ ] Test: Kill session works
  - [ ] Start session
  - [ ] Admin kills session
  - [ ] Verify session terminated
  - [ ] Verify toast shown
- [ ] Test: Kill all works
  - [ ] Start 5 sessions
  - [ ] Admin kills all
  - [ ] Verify all terminated
  - [ ] Verify count shown
- [ ] Test: Audit trail works
  - [ ] Kill session
  - [ ] Visit /admin/sessions/killed
  - [ ] Verify entry shown

**Validation**:
- [ ] Kill session action works (with confirmation)
- [ ] Kill all action works (double confirmation)
- [ ] Audit trail logged correctly
- [ ] UI updates correctly after kill

**Tests**:
Manual testing + Playwright E2E

---

### Day 69: Alert Configuration (ntfy.sh UI)

**Value**: Admin can configure alert thresholds from UI

#### Alert Settings Page

- [ ] Create `src/routes/(admin)/admin/settings/alerts/+page.svelte`
  - [ ] Display current alert thresholds
    - [ ] Runaway duration (warning, critical)
    - [ ] Runaway cost (warning, critical)
    - [ ] Cost spike percentage (alert if >X%)
  - [ ] Edit thresholds (forms)
  - [ ] Save to database (admin settings table)

#### Alert History

- [ ] Create `src/routes/(admin)/admin/alerts/history/+page.svelte`
  - [ ] Load all alerts from database
  - [ ] Display in table:
    - [ ] Timestamp
    - [ ] Type (runaway, cost_spike, error)
    - [ ] Severity (warning, critical)
    - [ ] Message
    - [ ] Session ID (if applicable)
    - [ ] Action taken (auto-kill, notified)

#### Test Alert

- [ ] Add "Send Test Alert" button
  - [ ] Sends test notification to ntfy.sh
  - [ ] Verifies admin phone receives it
  - [ ] Shows success/failure in UI

#### Testing

- [ ] Test: Alert settings page loads
  - [ ] Visit /admin/settings/alerts
  - [ ] Verify current thresholds displayed
- [ ] Test: Can edit thresholds
  - [ ] Change runaway duration
  - [ ] Save
  - [ ] Verify updated in database
- [ ] Test: Test alert works
  - [ ] Click "Send Test Alert"
  - [ ] Verify notification received on phone

**Validation**:
- [ ] Alert settings page works
- [ ] Thresholds editable (saved to DB)
- [ ] Test alert works (ntfy.sh receives)
- [ ] Alert history displays correctly

**Tests**:
Manual testing

---

### Day 70: Admin Dashboard Home

**Value**: At-a-glance system health

#### Dashboard Overview

- [ ] Create `src/routes/(admin)/admin/dashboard/+page.svelte`
  - [ ] Display key metrics (cards):
    - [ ] Active sessions (count, link to /admin/sessions/active)
    - [ ] Total cost today (vs yesterday)
    - [ ] Sessions today (vs yesterday)
    - [ ] Active users today (vs yesterday)
  - [ ] Display status indicators:
    - [ ] API status (healthy/unhealthy)
    - [ ] Redis status (healthy/unhealthy)
    - [ ] PostgreSQL status (healthy/unhealthy)
    - [ ] Anthropic API status (healthy/unhealthy)
  - [ ] Display recent alerts (last 10)
    - [ ] Link to full alert history

#### Quick Actions

- [ ] Add quick action buttons:
  - [ ] View active sessions
  - [ ] View cost analytics
  - [ ] Send test alert
  - [ ] Kill all sessions (emergency)

#### Auto-refresh

- [ ] Poll metrics every 10 seconds
  - [ ] Update counts, status indicators
  - [ ] Highlight changes (flash animation)

#### Testing

- [ ] Test: Dashboard loads
  - [ ] Visit /admin/dashboard
  - [ ] Verify metrics displayed
- [ ] Test: Auto-refresh works
  - [ ] Start new session
  - [ ] Verify count updates within 10 seconds
- [ ] Test: Quick actions work
  - [ ] Click each quick action
  - [ ] Verify navigation/action works

**Validation**:
- [ ] Dashboard displays correctly
- [ ] Metrics accurate
- [ ] Auto-refresh works (10s interval)
- [ ] Quick actions work

**Tests**:
Manual testing

---

### Day 71-77: Polish, Testing, Documentation

**Value**: Production-ready admin dashboard

#### Days 71-73: UI Polish

- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Dark mode support (admin dashboard)
- [ ] Accessibility (ARIA labels, keyboard navigation)
- [ ] Loading states (skeletons, spinners)
- [ ] Error states (empty states, error messages)
- [ ] Animations (smooth transitions)

#### Days 74-75: Testing

- [ ] Unit tests (admin API client)
- [ ] Integration tests (admin endpoints)
- [ ] E2E tests (Playwright)
  - [ ] Test: Admin login
  - [ ] Test: View active sessions
  - [ ] Test: Kill session
  - [ ] Test: View cost analytics
  - [ ] Test: Manage users
- [ ] Manual testing (full admin workflows)

#### Days 76-77: Documentation

- [ ] Update `README.md`
  - [ ] Admin dashboard features
  - [ ] How to access admin dashboard
  - [ ] Admin workflows (kill session, change tier, etc.)
- [ ] Create `zzz_project/ADMIN_DASHBOARD_COMPLETE.md`
  - [ ] Features implemented
  - [ ] Screenshots (optional)
  - [ ] Known limitations
  - [ ] Future enhancements

**Validation**:
- [ ] Admin dashboard fully functional
- [ ] All tests pass (unit, integration, E2E)
- [ ] Documentation complete
- [ ] UI polished (responsive, accessible)

**Go/No-Go for Week 12**:
- [ ] ✅ Admin dashboard works (all features)
- [ ] ✅ Kill switches work (single + all)
- [ ] ✅ Cost analytics accurate
- [ ] ✅ User management works
- [ ] ✅ Alert history displayed

---

## Week 12 (Days 78-84): Email Templates + Final Integrations

**Goal**: Complete Resend integration with all email templates

**Status**: 0/42 tasks complete

### Day 78: Welcome Email Template

**Value**: Onboard new users with helpful email

#### Template Design

- [ ] Create HTML email template
  - [ ] Welcome headline
  - [ ] Getting started steps (3-5 bullets)
  - [ ] Link to first deliberation
  - [ ] Link to documentation
  - [ ] Unsubscribe link (legal requirement)
- [ ] Create plain text version (fallback)
- [ ] Test rendering in email clients (Gmail, Outlook, Apple Mail)

#### Implementation

- [ ] Update `backend/services/email_templates.py`
  - [ ] `render_welcome_email()` - Returns HTML + plain text
  - [ ] Use template engine (Jinja2) for variables
  - [ ] Variables: user_name, dashboard_url, docs_url
- [ ] Test email sending
  - [ ] Trigger welcome email on signup
  - [ ] Verify HTML rendering
  - [ ] Verify plain text fallback

**Validation**:
- [ ] Template renders correctly (HTML + plain text)
- [ ] Email delivers to inbox (not spam)
- [ ] Links work (dashboard, docs)
- [ ] Unsubscribe link works

**Tests**:
Manual testing (check inbox)

---

### Day 79: Deliberation Complete Email

**Value**: Notify user when deliberation finishes

#### Template Design

- [ ] Create email template
  - [ ] Subject: "Your deliberation is complete"
  - [ ] Summary:
    - [ ] Problem statement (truncated)
    - [ ] Recommendation (short version)
    - [ ] Key insights (3-5 bullets)
  - [ ] CTA: "View Full Report" (link to session page)
  - [ ] Metrics: Rounds, cost, duration (optional)

#### Trigger

- [ ] Send email when deliberation completes
  - [ ] In synthesis node (after synthesis complete)
  - [ ] Or: In webhook (deliberation.completed event)
- [ ] Only send if user has emails enabled (preferences)

#### Testing

- [ ] Test: Email sends on deliberation complete
  - [ ] Run full deliberation
  - [ ] Verify email received
  - [ ] Verify content correct
- [ ] Test: Email not sent if user disabled emails
  - [ ] Disable emails in preferences
  - [ ] Run deliberation
  - [ ] Verify no email sent

**Validation**:
- [ ] Email sends on completion
- [ ] Template renders correctly
- [ ] CTA link works (session page)
- [ ] Respects user preferences

**Tests**:
Manual testing + integration test

---

### Day 80: Payment Receipt Email

**Value**: Confirm successful payment

#### Template Design

- [ ] Create email template
  - [ ] Subject: "Payment receipt from Board of One"
  - [ ] Thank you message
  - [ ] Invoice details:
    - [ ] Date, amount, payment method (last 4 digits)
    - [ ] Plan: Pro ($29/month)
    - [ ] Billing period (next charge date)
  - [ ] Links:
    - [ ] View invoice (Stripe hosted invoice)
    - [ ] Manage billing (Stripe customer portal)

#### Trigger

- [ ] Send on `invoice.paid` Stripe webhook
  - [ ] Extract invoice details
  - [ ] Render template
  - [ ] Send via Resend

#### Testing

- [ ] Test: Email sends on payment
  - [ ] Complete test checkout (Stripe)
  - [ ] Verify email received
  - [ ] Verify invoice link works
- [ ] Test: Email includes correct details
  - [ ] Amount, date, plan

**Validation**:
- [ ] Email sends on payment
- [ ] Invoice details correct
- [ ] Links work (invoice, billing portal)

**Tests**:
Manual testing with Stripe test mode

---

### Day 81: Session Paused/Resumed Emails

**Value**: Notify user when session state changes

#### Template Design (Paused)

- [ ] Create email template
  - [ ] Subject: "Your deliberation is paused"
  - [ ] Message: Session paused, checkpoint saved
  - [ ] CTA: "Resume Deliberation" (link to session page)
  - [ ] Note: Session expires after 7 days

#### Template Design (Resumed)

- [ ] Create email template
  - [ ] Subject: "Your deliberation has resumed"
  - [ ] Message: Session resumed from checkpoint
  - [ ] CTA: "View Progress" (link to session page)

#### Trigger

- [ ] Send on pause/resume events
  - [ ] In pause endpoint (after checkpoint saved)
  - [ ] In resume endpoint (after graph restarts)
- [ ] Only send if user has emails enabled

#### Testing

- [ ] Test: Paused email sends
  - [ ] Pause deliberation
  - [ ] Verify email received
- [ ] Test: Resumed email sends
  - [ ] Resume deliberation
  - [ ] Verify email received

**Validation**:
- [ ] Emails send on pause/resume
- [ ] Templates render correctly
- [ ] CTAs work (session page)

**Tests**:
Manual testing

---

### Day 82: Session Expired Email

**Value**: Notify user when paused session expires

#### Template Design

- [ ] Create email template
  - [ ] Subject: "Your paused deliberation has expired"
  - [ ] Message: Session paused for >7 days, checkpoint deleted
  - [ ] CTA: "Start New Deliberation"
  - [ ] Note: Data not recoverable

#### Trigger

- [ ] Create cleanup job (`backend/jobs/cleanup.py`)
  - [ ] Run daily (cron or background task)
  - [ ] Find sessions: `status=paused` AND `paused_at < NOW() - 7 days`
  - [ ] For each:
    - [ ] Send expiration email
    - [ ] Delete checkpoint
    - [ ] Mark session as expired

#### Testing

- [ ] Test: Cleanup job runs
  - [ ] Create paused session (manually set paused_at to 8 days ago)
  - [ ] Run cleanup job
  - [ ] Verify email sent
  - [ ] Verify checkpoint deleted
- [ ] Test: Expiration email correct
  - [ ] Verify subject, message, CTA

**Validation**:
- [ ] Cleanup job works (finds expired sessions)
- [ ] Email sends on expiration
- [ ] Checkpoint deleted
- [ ] Session marked as expired

**Tests**:
```bash
pytest backend/tests/test_cleanup_job.py -v
```

---

### Day 83: Email Preferences (Opt-out)

**Value**: Legal compliance (CAN-SPAM, GDPR)

#### Preferences Page

- [ ] Create `src/routes/(app)/settings/notifications/+page.svelte`
  - [ ] Toggle: "Welcome emails" (on/off)
  - [ ] Toggle: "Deliberation complete emails" (on/off)
  - [ ] Toggle: "Session state change emails" (on/off)
  - [ ] Toggle: "Marketing emails" (on/off)
  - [ ] Button: "Save Preferences"

#### Database

- [ ] Add `email_preferences` field to `users` table
  ```sql
  ALTER TABLE users ADD COLUMN email_preferences JSONB DEFAULT '{
      "welcome": true,
      "deliberation_complete": true,
      "session_state_change": true,
      "marketing": false
  }';
  ```

#### Unsubscribe Link

- [ ] Add unsubscribe link to all emails
  - [ ] Link: `https://app.boardofone.com/unsubscribe?token={token}`
  - [ ] Token: JWT with user_id + email_type
  - [ ] On click: Disable that email type for user
  - [ ] Show confirmation page

#### Testing

- [ ] Test: Preferences page works
  - [ ] Toggle "Deliberation complete emails"
  - [ ] Save
  - [ ] Verify updated in database
- [ ] Test: Unsubscribe link works
  - [ ] Click unsubscribe link in email
  - [ ] Verify preference updated
  - [ ] Verify confirmation page shown
- [ ] Test: Emails respect preferences
  - [ ] Disable "Deliberation complete emails"
  - [ ] Run deliberation
  - [ ] Verify no email sent

**Validation**:
- [ ] Preferences page works
- [ ] Unsubscribe link works
- [ ] Emails respect preferences
- [ ] Legal compliance (CAN-SPAM, GDPR)

**Tests**:
Manual testing + integration tests

---

### Day 84: Week 12 Polish + Pre-commit

**Value**: Email system complete and tested

#### Email Testing

- [ ] Test all email templates
  - [ ] Welcome email
  - [ ] Deliberation complete email
  - [ ] Payment receipt email
  - [ ] Session paused email
  - [ ] Session resumed email
  - [ ] Session expired email
- [ ] Test in multiple email clients
  - [ ] Gmail (web + mobile)
  - [ ] Outlook (web + desktop)
  - [ ] Apple Mail (iOS + macOS)
  - [ ] Yahoo Mail
- [ ] Verify deliverability
  - [ ] Check spam score (mail-tester.com)
  - [ ] Verify DKIM, SPF, DMARC pass
  - [ ] Verify unsubscribe link works

#### Code Quality

- [ ] Run pre-commit checks
  ```bash
  make pre-commit
  ```
- [ ] Fix all issues
- [ ] Ensure test coverage >90%

#### Documentation

- [ ] Update `README.md`
  - [ ] Email integration complete
  - [ ] Email templates documented
  - [ ] Unsubscribe flow documented
- [ ] Create `zzz_project/WEEK12_EMAIL_COMPLETE.md`
  - [ ] All email templates implemented
  - [ ] Deliverability verified
  - [ ] Legal compliance checklist

**Validation**:
- [ ] All email templates work
- [ ] Deliverability >95% (not spam)
- [ ] Unsubscribe flow works
- [ ] All pre-commit checks pass

**Go/No-Go for Week 13**:
- [ ] ✅ All emails deliver to inbox (not spam)
- [ ] ✅ Templates render correctly (all clients)
- [ ] ✅ Unsubscribe flow works
- [ ] ✅ Legal compliance verified (CAN-SPAM, GDPR)

---

## Week 13 (Days 85-91): QA + Security Audit

**Goal**: Production-ready system, security audited, load tested

**Status**: 0/56 tasks complete

### Day 85: Load Testing

**Value**: Verify system handles production load

#### Load Test Scenarios

- [ ] Scenario 1: Normal load
  - [ ] 10 concurrent users
  - [ ] Each creates 1 deliberation
  - [ ] Measure: API latency, DB queries, Redis ops
  - [ ] Target: <500ms p95 latency
- [ ] Scenario 2: Peak load
  - [ ] 50 concurrent users
  - [ ] Each creates 1 deliberation
  - [ ] Measure: Same as above
  - [ ] Target: <1s p95 latency
- [ ] Scenario 3: Sustained load
  - [ ] 20 concurrent users
  - [ ] 1 hour duration
  - [ ] Measure: Memory leaks, DB connection pool
  - [ ] Target: No errors, stable memory

#### Load Testing Tool

- [ ] Install Locust
  ```bash
  pip install locust
  ```
- [ ] Create `tests/load/locustfile.py`
  - [ ] Define user behavior:
    - [ ] Create session
    - [ ] Start deliberation
    - [ ] Poll status until complete
  - [ ] Run test:
    ```bash
    locust -f tests/load/locustfile.py --host=http://localhost:8000
    ```

#### Results Analysis

- [ ] Collect metrics:
  - [ ] API latency (p50, p95, p99)
  - [ ] Error rate (%)
  - [ ] Database query time
  - [ ] Redis operation time
  - [ ] Memory usage (MB)
- [ ] Identify bottlenecks
  - [ ] Slow queries (use EXPLAIN)
  - [ ] Redis hotkeys (use MONITOR)
  - [ ] Slow endpoints (use profiler)
- [ ] Optimize hot paths
  - [ ] Add indexes (if needed)
  - [ ] Cache frequently accessed data
  - [ ] Optimize slow queries

#### Testing

- [ ] Test: Normal load passes
  - [ ] Run Scenario 1
  - [ ] Verify <500ms p95 latency
- [ ] Test: Peak load passes
  - [ ] Run Scenario 2
  - [ ] Verify <1s p95 latency
- [ ] Test: Sustained load passes
  - [ ] Run Scenario 3 (1 hour)
  - [ ] Verify no errors
  - [ ] Verify stable memory

**Validation**:
- [ ] Normal load: <500ms p95 latency
- [ ] Peak load: <1s p95 latency
- [ ] Sustained load: No errors, stable memory
- [ ] Bottlenecks identified and optimized

**Tests**:
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5
```

---

### Day 86: Security Audit - Authentication

**Value**: Verify auth system secure

#### Auth Security Checklist

- [ ] Session security
  - [ ] Verify: httpOnly cookies (not accessible via JS)
  - [ ] Verify: secure flag (HTTPS only)
  - [ ] Verify: sameSite=lax (CSRF protection)
  - [ ] Verify: short expiration (1 hour access token)
  - [ ] Verify: refresh token rotation enabled
- [ ] OAuth security
  - [ ] Verify: state parameter prevents CSRF
  - [ ] Verify: redirect URI validated (no open redirects)
  - [ ] Verify: PKCE enabled (if supported)
- [ ] Password security (if email/password enabled)
  - [ ] Verify: Minimum 12 characters
  - [ ] Verify: bcrypt with 10+ rounds
  - [ ] Verify: No password hints or weak resets
- [ ] Rate limiting
  - [ ] Verify: Max 5 login attempts per 5 min per IP
  - [ ] Verify: Max 3 password reset requests per hour

#### Penetration Testing

- [ ] Test: Session fixation attack
  - [ ] Try reusing old session after login
  - [ ] Verify: New session ID generated
- [ ] Test: CSRF attack
  - [ ] Try POST request without CSRF token
  - [ ] Verify: 403 Forbidden
- [ ] Test: Session hijacking
  - [ ] Try using stolen session cookie
  - [ ] Verify: Expires after 1 hour
- [ ] Test: Brute force login
  - [ ] Attempt 10 logins in 1 minute
  - [ ] Verify: Rate limit triggered after 5 attempts

**Validation**:
- [ ] All auth checklist items pass
- [ ] All penetration tests pass (attacks blocked)
- [ ] No auth vulnerabilities found

**Tests**:
Manual penetration testing + automated security scans

---

### Day 87: Security Audit - API & Data

**Value**: Verify API and data access secure

#### API Security Checklist

- [ ] Authorization
  - [ ] Verify: Users can only access own sessions (RLS)
  - [ ] Verify: Admins require admin key (X-Admin-Key header)
  - [ ] Verify: Vertical privilege escalation blocked (user can't access admin endpoints)
  - [ ] Verify: Horizontal privilege escalation blocked (user can't access other users' sessions)
- [ ] Input validation
  - [ ] Verify: All inputs validated (Pydantic models)
  - [ ] Verify: SQL injection prevented (parameterized queries)
  - [ ] Verify: XSS prevented (Svelte auto-escaping)
  - [ ] Verify: File upload attacks prevented (no file uploads in MVP)
- [ ] Rate limiting
  - [ ] Verify: Per-user limits enforced (free, pro, enterprise)
  - [ ] Verify: Per-IP limits enforced (DDoS protection)
- [ ] Sensitive data
  - [ ] Verify: Stripe secret key never exposed to client
  - [ ] Verify: Supabase service role key server-side only
  - [ ] Verify: Anthropic API key server-side only

#### Penetration Testing

- [ ] Test: Access other user's session
  - [ ] Try GET /api/v1/sessions/{other_user_session_id}
  - [ ] Verify: 403 Forbidden (RLS blocks)
- [ ] Test: Access admin endpoint without key
  - [ ] Try GET /api/admin/sessions/active (no X-Admin-Key)
  - [ ] Verify: 403 Forbidden
- [ ] Test: SQL injection
  - [ ] Try: `GET /api/v1/sessions?status=' OR '1'='1`
  - [ ] Verify: No SQL injection (parameterized queries)
- [ ] Test: XSS injection
  - [ ] Try: Create session with `<script>alert('XSS')</script>` in problem statement
  - [ ] Verify: Script not executed (auto-escaped)

**Validation**:
- [ ] All API security checklist items pass
- [ ] All penetration tests pass (attacks blocked)
- [ ] No API vulnerabilities found

**Tests**:
Manual penetration testing + automated security scans (OWASP ZAP)

---

### Day 88: Security Audit - Infrastructure

**Value**: Verify infrastructure secure

#### Infrastructure Security Checklist

- [ ] Network security
  - [ ] Verify: All traffic HTTPS (TLS 1.3)
  - [ ] Verify: HSTS header enabled (force HTTPS)
  - [ ] Verify: Database not publicly accessible (VPN/private network only)
  - [ ] Verify: Redis not publicly accessible
- [ ] Secrets management
  - [ ] Verify: No secrets in code (gitignored .env)
  - [ ] Verify: No secrets in Docker images (ARG, not ENV)
  - [ ] Verify: Secrets encrypted at rest (Doppler or AWS Secrets Manager)
  - [ ] Verify: Secrets rotated quarterly
- [ ] Logging
  - [ ] Verify: No PII in logs (emails, IPs scrubbed)
  - [ ] Verify: Structured logs (JSON)
  - [ ] Verify: Log retention <30 days (compliance)
- [ ] Monitoring
  - [ ] Verify: Alerts configured (ntfy.sh)
  - [ ] Verify: Error tracking (Sentry, if enabled)
  - [ ] Verify: Health checks (ready, live, startup)

#### Dependency Scanning

- [ ] Scan Python dependencies
  ```bash
  uv pip install safety
  safety check --json
  ```
- [ ] Scan npm dependencies
  ```bash
  npm audit
  ```
- [ ] Fix critical vulnerabilities (upgrade packages)

**Validation**:
- [ ] All infrastructure checklist items pass
- [ ] No critical vulnerabilities in dependencies
- [ ] No secrets exposed

**Tests**:
```bash
safety check
npm audit
```

---

### Day 89: GDPR Compliance Audit

**Value**: Verify legal compliance

#### GDPR Checklist

- [ ] Data minimization
  - [ ] Verify: Only necessary data collected
  - [ ] Verify: No tracking pixels or analytics cookies (without consent)
- [ ] User rights
  - [ ] Verify: User can export data (JSON download)
  - [ ] Verify: User can delete account (anonymization, not hard delete)
  - [ ] Verify: User can opt-out of emails (preferences page + unsubscribe link)
- [ ] Data retention
  - [ ] Verify: Sessions expire after 365 days (inactive users)
  - [ ] Verify: Audit logs retained 7 years
  - [ ] Verify: Anonymized data retained indefinitely (analytics)
- [ ] Data processing agreements (DPAs)
  - [ ] Verify: Supabase DPA signed
  - [ ] Verify: Anthropic DPA signed (covered by their policy)
  - [ ] Verify: Stripe DPA signed
  - [ ] Verify: Resend DPA signed
- [ ] Privacy policy
  - [ ] Verify: Published at /privacy-policy
  - [ ] Verify: Covers all data processing
  - [ ] Verify: Links to DPO (if required)
  - [ ] Verify: Right to lodge complaint with supervisory authority

#### Testing

- [ ] Test: User can export data
  - [ ] Click "Export Data" in settings
  - [ ] Verify JSON download
  - [ ] Verify all user data included
- [ ] Test: User can delete account
  - [ ] Click "Delete Account" in settings
  - [ ] Verify anonymization (not hard delete)
  - [ ] Verify PII removed
- [ ] Test: User can opt-out of emails
  - [ ] Click unsubscribe link
  - [ ] Verify preference updated
  - [ ] Verify no more emails sent

**Validation**:
- [ ] All GDPR checklist items pass
- [ ] User rights work (export, delete, opt-out)
- [ ] Privacy policy complete
- [ ] DPAs signed

**Tests**:
Manual testing + legal review

---

### Day 90: E2E Testing (Playwright)

**Value**: Verify critical user flows work

#### E2E Test Setup

- [ ] Install Playwright
  ```bash
  npm install -D @playwright/test
  npx playwright install
  ```
- [ ] Create test file: `tests/e2e/user_flows.spec.ts`

#### Critical Flows

- [ ] Test: User signup and login
  - [ ] Sign up with email
  - [ ] Confirm email
  - [ ] Log in
  - [ ] Verify dashboard loads
- [ ] Test: Create deliberation
  - [ ] Click "New Deliberation"
  - [ ] Enter problem statement
  - [ ] Submit
  - [ ] Verify deliberation starts
  - [ ] Wait for completion
  - [ ] Verify results displayed
- [ ] Test: Pause and resume
  - [ ] Start deliberation
  - [ ] Click "Pause"
  - [ ] Verify checkpoint saved
  - [ ] Click "Resume"
  - [ ] Verify continues from checkpoint
- [ ] Test: Upgrade to Pro
  - [ ] Click "Upgrade to Pro"
  - [ ] Complete Stripe checkout (test card)
  - [ ] Verify redirected to success page
  - [ ] Verify tier updated to Pro
- [ ] Test: Admin dashboard
  - [ ] Log in as admin
  - [ ] View active sessions
  - [ ] Kill session
  - [ ] View cost analytics
  - [ ] Verify data correct

#### Run Tests

- [ ] Run E2E tests
  ```bash
  npx playwright test
  ```
- [ ] Generate HTML report
  ```bash
  npx playwright show-report
  ```

**Validation**:
- [ ] All critical flows pass
- [ ] No flaky tests (run 3 times, all pass)
- [ ] Screenshots captured on failure

**Tests**:
```bash
npx playwright test tests/e2e/user_flows.spec.ts
```

---

### Day 91: Privacy Policy, Terms, CI/CD & Deployment Setup

**Goal**: Create legal documents, automation pipeline, and deployment infrastructure

**Tasks**:

#### Privacy Policy & Terms of Service (GDPR Art. 13-14)
- [ ] Draft privacy policy covering:
  - [ ] Identity of data controller (Board of One, Inc.)
  - [ ] Contact details (support@boardofone.com)
  - [ ] Purposes of processing (provide deliberation service)
  - [ ] Legal basis (contract performance, consent, legitimate interest)
  - [ ] Data retention periods (365 days default)
  - [ ] User rights (access, erasure, portability, object)
  - [ ] Right to lodge complaint (supervisory authority)
  - [ ] Data processors: Supabase, Anthropic, Stripe, Resend, Sentry
- [ ] Legal review (lawyer or use template service like Termly)
- [ ] Create page: src/routes/privacy-policy/+page.svelte
- [ ] Link in footer
- [ ] Draft terms of service covering:
  - [ ] Service description
  - [ ] User obligations
  - [ ] Subscription terms and billing
  - [ ] Cancellation policy
  - [ ] Limitation of liability
  - [ ] Dispute resolution
- [ ] Create page: src/routes/terms-of-service/+page.svelte
- [ ] Link in footer

#### Data Processing Agreements (DPAs)
- [ ] Sign DPA with Supabase (https://supabase.com/dpa)
- [ ] Verify Anthropic data policy (they don't retain data)
- [ ] Verify Stripe GDPR compliance (already compliant)
- [ ] Sign DPA with Resend (https://resend.com/dpa)
- [ ] Sign DPA with Sentry (if using)
- [ ] Document all processors in privacy policy

#### CI/CD Pipeline Setup
- [ ] Create .github/workflows/test.yml
  ```yaml
  name: Tests
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v4
          with:
            python-version: '3.12'
        - name: Install uv
          run: pip install uv
        - name: Install dependencies
          run: uv sync --frozen
        - name: Run linting
          run: make lint
        - name: Run type checking
          run: make typecheck
        - name: Run tests
          run: make test
  ```
- [ ] Create .github/workflows/deploy-staging.yml (on merge to main)
- [ ] Create .github/workflows/deploy-production.yml (on tag v*)
- [ ] Configure secrets in GitHub (API keys, credentials)
- [ ] Test: Push to branch, verify CI runs
- [ ] Test: Merge to main, verify staging deployment
- [ ] Test: Create tag v0.1.0, verify production deployment

#### DNS & SSL Setup
- [ ] Purchase boardofone.com (Namecheap or Cloudflare Registrar)
- [ ] Configure DNS records:
  ```
  A      @                → DigitalOcean IP (after deployment)
  CNAME  www              → @
  CNAME  api              → @
  TXT    @                → SPF: v=spf1 include:resend.com ~all
  TXT    resend._domainkey → [DKIM from Resend]
  TXT    _dmarc           → v=DMARC1; p=none; rua=mailto:security@boardofone.com
  ```
- [ ] Verify DNS propagation: `dig boardofone.com`
- [ ] Setup Let's Encrypt (auto-provisioned by DigitalOcean App Platform)
- [ ] Test HTTPS redirect

#### Backup & Disaster Recovery
- [ ] PostgreSQL: Enable daily automated backups (Supabase Pro)
  - [ ] Retention: 30 days
  - [ ] Point-in-time recovery (PITR)
- [ ] Redis: AOF + RDB snapshots
  - [ ] AOF: appendfsync everysec
  - [ ] RDB: save every 5 minutes
- [ ] Test backup restore procedure:
  ```bash
  # Test PostgreSQL restore
  pg_restore -d boardofone_test backups/backup-2025-11-14.sql

  # Test Redis restore
  redis-cli --rdb backups/dump.rdb
  ```
- [ ] Document disaster recovery plan (RTO: 4 hours, RPO: 1 hour)
- [ ] Create runbook: docs/DISASTER_RECOVERY.md

#### Uptime Monitoring
- [ ] Setup UptimeRobot (free tier) or Better Uptime
- [ ] Monitor /health endpoint (5-minute interval)
- [ ] Monitor /api/health/db (database health)
- [ ] Monitor /api/health/redis (Redis health)
- [ ] Configure alerts:
  - [ ] Email: team@boardofone.com
  - [ ] SMS: [optional]
  - [ ] Slack webhook: [optional]
- [ ] Target: 99.9% uptime (8.7 hours/year downtime allowed)

#### Incident Response Playbook
- [ ] Create docs/INCIDENT_RESPONSE_PLAYBOOK.md
- [ ] Document procedures for common incidents:
  - [ ] Database Down (detection, impact, recovery, ETA)
  - [ ] Redis Down (detection, impact, recovery, ETA)
  - [ ] API Down (detection, impact, recovery, ETA)
  - [ ] Runaway Session (detection, impact, recovery, ETA)
  - [ ] Data Breach (detection, impact, GDPR notification, recovery)

**Validation**:
- [ ] Privacy policy published at /privacy-policy
- [ ] Terms of service published at /terms-of-service
- [ ] All DPAs signed and documented
- [ ] CI runs on every push
- [ ] Tests must pass before merge
- [ ] Staging deploys automatically on merge
- [ ] Production deploys on git tag only
- [ ] DNS resolves correctly
- [ ] HTTPS works, redirects HTTP
- [ ] Backup restore tested successfully
- [ ] Uptime monitoring active
- [ ] Incident playbook covers all 5 scenarios

**Deliverables**:
- src/routes/privacy-policy/+page.svelte
- src/routes/terms-of-service/+page.svelte
- docs/DATA_PROCESSORS.md
- .github/workflows/test.yml
- .github/workflows/deploy-staging.yml
- .github/workflows/deploy-production.yml
- docs/CI_CD_SETUP.md
- docs/DISASTER_RECOVERY.md
- docs/INCIDENT_RESPONSE_PLAYBOOK.md

---

### Day 92: Integration & Security Testing + Deployment Documentation

**Goal**: Validate end-to-end flows and security hardening

**Tasks**:

#### End-to-End Integration Tests
- [ ] Install Playwright: `npm install -D @playwright/test`
- [ ] Create E2E test: Complete user journey
  ```typescript
  test('complete user journey', async ({ page }) => {
    // Sign up with Google OAuth
    await page.goto('/signup');
    await page.click('text=Sign up with Google');
    // ... complete OAuth flow

    // Create deliberation
    await page.fill('[name="problem"]', 'Should I...');
    await page.click('text=Start Deliberation');

    // Wait for completion
    await page.waitForSelector('text=Deliberation Complete');

    // Export results
    await page.click('text=Export JSON');
    const download = await page.waitForEvent('download');
  });
  ```
- [ ] Test: Cross-service integration (FastAPI + SvelteKit + Redis + PostgreSQL)
- [ ] Test: WebSocket/SSE streaming works
- [ ] Test: Checkpoint recovery works

#### Load Testing
- [ ] Install Locust: `uv add locust`
- [ ] Create load test script (tests/load/deliberation_load.py)
  ```python
  from locust import HttpUser, task, between

  class DeliberationUser(HttpUser):
      wait_time = between(1, 3)

      @task
      def create_deliberation(self):
          self.client.post("/api/v1/sessions", json={
              "problem": "Should I invest in AI?"
          })
  ```
- [ ] Run load test: 100 concurrent users
- [ ] Target metrics:
  - [ ] P50 latency: <500ms
  - [ ] P95 latency: <2s
  - [ ] P99 latency: <5s
  - [ ] Error rate: <1%
- [ ] Identify bottlenecks, optimize if needed

#### Security Testing (OWASP Top 10)
- [ ] SQL Injection tests
  ```bash
  # Test parameterized queries (should be immune)
  curl -X POST http://localhost:8000/api/v1/sessions \
    -d '{"problem": "test'; DROP TABLE sessions; --"}'
  # Expect: 400 Bad Request (Pydantic validation)
  ```
- [ ] XSS tests
  ```bash
  # Test HTML escaping
  curl -X POST http://localhost:8000/api/v1/sessions \
    -d '{"problem": "<script>alert(1)</script>"}'
  # Expect: Escaped in response
  ```
- [ ] CSRF tests (verify SameSite cookies)
- [ ] Auth bypass tests
  ```bash
  # Test without token
  curl http://localhost:8000/api/v1/sessions
  # Expect: 401 Unauthorized

  # Test with expired token
  curl -H "Authorization: Bearer $EXPIRED_TOKEN" http://localhost:8000/api/v1/sessions
  # Expect: 401 Unauthorized
  ```
- [ ] Rate limit tests (verify 429 returned)

#### Deployment Documentation
- [ ] Document production deployment steps (docs/DEPLOYMENT.md):
  1. [ ] Pre-deployment checklist
  2. [ ] Database migration procedure
  3. [ ] Environment variable configuration
  4. [ ] DigitalOcean App Platform setup
  5. [ ] DNS configuration
  6. [ ] SSL verification
  7. [ ] Health check verification
  8. [ ] Rollback procedure
- [ ] Create deployment checklist
- [ ] Document rollback procedure

**Validation**:
- [ ] E2E test passes (signup → deliberation → export)
- [ ] Load test achieves target metrics
- [ ] All OWASP tests pass (no vulnerabilities)
- [ ] Security headers present
- [ ] Deployment documentation complete

**Tests**:
```bash
# Run E2E tests
npx playwright test

# Run load test
locust -f tests/load/deliberation_load.py --host=http://localhost:8000 --users=100

# Run security tests
pytest tests/test_security.py -v
```

**Deliverables**:
- tests/e2e/ (Playwright tests)
- tests/load/ (Locust load tests)
- tests/test_security.py (OWASP tests)
- docs/LOAD_TEST_RESULTS.md
- docs/SECURITY_AUDIT.md
- docs/DEPLOYMENT.md

#### Blue-Green Deployment (Zero-Downtime)

**Value**: Deploy new versions without user-facing downtime

**Tasks**:
- [ ] Setup blue and green environments (DigitalOcean App Platform)
  ```yaml
  # Blue environment (current production)
  name: boardofone-blue
  services:
    - name: api-blue
      image: ghcr.io/boardofone/api:v1.2.3

  # Green environment (new version)
  name: boardofone-green
  services:
    - name: api-green
      image: ghcr.io/boardofone/api:v1.2.4
  ```
- [ ] Deploy new version to green (inactive)
- [ ] Run smoke tests against green environment
  ```bash
  # Test green environment health
  curl https://green.boardofone.com/health

  # Run integration tests
  pytest tests/test_green_environment.py --env=green
  ```
- [ ] Database migrations (run before traffic switch)
  ```python
  # Ensure migrations are backward-compatible
  # Blue (old code) must work with new schema
  alembic upgrade head
  ```
- [ ] Switch traffic from blue to green (DNS or load balancer)
  ```bash
  # Option 1: DNS switch (slow, 5-10 min TTL)
  # Option 2: Load balancer (instant)

  # DigitalOcean App Platform
  doctl apps update $APP_ID --active-deployment green
  ```
- [ ] Monitor green environment (5 minutes)
  - Check error rate <1%
  - Check latency P95 <2s
  - Check active sessions (no drops)
- [ ] Rollback procedure if green fails
  ```bash
  # Switch traffic back to blue
  doctl apps update $APP_ID --active-deployment blue

  # Rollback database migration (if needed)
  alembic downgrade -1
  ```
- [ ] Decommission blue environment after 24h (if green stable)

**Validation**:
- [ ] New version deployed to green without affecting production
- [ ] Smoke tests pass on green before traffic switch
- [ ] Traffic switch completes in <30 seconds
- [ ] Zero user-facing errors during switch
- [ ] Rollback tested (switch back to blue works)

**Tests**:
```bash
# Test blue-green deployment (staging)
./scripts/deploy-blue-green.sh --env=staging --version=v1.2.4

# Verify zero downtime
./scripts/test-zero-downtime.sh
```

**Deliverables**:
- scripts/deploy-blue-green.sh
- docs/BLUE_GREEN_DEPLOYMENT.md
- .github/workflows/deploy-blue-green.yml

**Go/No-Go for Week 14**:
- [ ] ✅ Load testing passes (all scenarios)
- [ ] ✅ Security audits pass (no critical vulnerabilities)
- [ ] ✅ GDPR compliance verified
- [ ] ✅ E2E tests pass (all critical flows)
- [ ] ✅ Documentation complete
- [ ] ✅ Deployment procedure tested
- [ ] ✅ Blue-green deployment working

---

## Week 14 (Days 93-101): Launch Preparation + User Documentation

**Goal**: Deploy to production, create user docs, announce launch, monitor closely

**Status**: 0/77 tasks complete

### Day 93-94: User Documentation & Help Center

**Goal**: Create comprehensive user-facing documentation

**Tasks**:
- [ ] Create help center page (src/routes/help/+page.svelte)
- [ ] Write documentation:
  1. **Getting Started**
     - [ ] How to sign up
     - [ ] Creating your first deliberation
     - [ ] Understanding the interface
  2. **How to Create a Deliberation**
     - [ ] Writing effective problem statements
     - [ ] Selecting personas (automatic vs manual)
     - [ ] Understanding rounds and voting
  3. **Understanding Personas**
     - [ ] List of 45 available personas
     - [ ] When to use each persona
     - [ ] Persona expertise areas
  4. **Interpreting Results**
     - [ ] Reading the synthesis
     - [ ] Understanding voting results
     - [ ] Exporting and sharing results
  5. **FAQ**
     - [ ] How does consensus work?
     - [ ] Can I pause a deliberation?
     - [ ] How much does it cost?
     - [ ] What happens to my data?
     - [ ] Can I delete my account?
  6. **Troubleshooting**
     - [ ] Deliberation taking too long (runaway detection)
     - [ ] Unable to resume session (checkpoint recovery)
     - [ ] Payment issues (Stripe support)
- [ ] Add search functionality (simple keyword search)
- [ ] Link from navigation and footer

**Validation**:
- [ ] All 6 documentation sections complete
- [ ] Search works for common queries
- [ ] Links from footer/navigation work

**Deliverables**:
- src/routes/help/+page.svelte
- src/routes/help/getting-started/+page.svelte
- src/routes/help/creating-deliberation/+page.svelte
- src/routes/help/understanding-personas/+page.svelte
- src/routes/help/interpreting-results/+page.svelte
- src/routes/help/faq/+page.svelte
- src/routes/help/troubleshooting/+page.svelte

---

### Day 95: DigitalOcean Deployment Setup

**Value**: Production infrastructure ready

#### DigitalOcean Setup

- [ ] Create DigitalOcean account
- [ ] Create Kubernetes cluster
  - [ ] Region: US East (or closest to users)
  - [ ] Node size: 2 CPU, 4 GB RAM (2 nodes)
  - [ ] Enable monitoring
  - [ ] Enable auto-scaling (min 2, max 5 nodes)
- [ ] Create managed PostgreSQL
  - [ ] Plan: Basic (1 CPU, 1 GB RAM)
  - [ ] Enable daily backups
  - [ ] Enable connection pooling (PgBouncer)
- [ ] Create managed Redis
  - [ ] Plan: Basic (1 CPU, 512 MB RAM)
  - [ ] Enable eviction policy (allkeys-lru)

#### DNS Configuration

- [ ] Point domain to DigitalOcean
  - [ ] Add A records:
    - [ ] `app.boardofone.com` → Load balancer IP
    - [ ] `api.boardofone.com` → Load balancer IP
  - [ ] Add CNAME records:
    - [ ] `www.boardofone.com` → `app.boardofone.com`
- [ ] Configure SSL (Let's Encrypt via Traefik)
  - [ ] Add cert-manager to Kubernetes
  - [ ] Configure Let's Encrypt issuer
  - [ ] Request wildcard cert (`*.boardofone.com`)

#### Testing

- [ ] Test: Kubernetes cluster accessible
  ```bash
  kubectl get nodes
  ```
- [ ] Test: PostgreSQL accessible
  ```bash
  psql $DATABASE_URL
  ```
- [ ] Test: Redis accessible
  ```bash
  redis-cli -u $REDIS_URL
  ```
- [ ] Test: DNS resolves
  ```bash
  nslookup app.boardofone.com
  ```

**Validation**:
- [ ] Kubernetes cluster running
- [ ] Managed databases created (PostgreSQL, Redis)
- [ ] DNS configured (A records, SSL)
- [ ] All resources accessible

**Tests**:
Manual testing via CLI

---

### Day 96: CI/CD Pipeline Setup

**Value**: Automated deployments

#### GitHub Actions Workflow

- [ ] Create `.github/workflows/deploy.yml`
  - [ ] Trigger: Push to `main` branch
  - [ ] Steps:
    1. Checkout code
    2. Run tests (pytest, npm test, playwright)
    3. Build Docker images (backend, frontend)
    4. Push images to DigitalOcean Container Registry
    5. Deploy to Kubernetes (kubectl apply)
    6. Run smoke tests (health checks)
    7. Notify success/failure (ntfy.sh)

#### Smoke Tests

- [ ] Create `scripts/smoke_test.sh`
  - [ ] Test: Health check endpoint (200 OK)
  - [ ] Test: Create session (API call)
  - [ ] Test: Start deliberation (verify runs)
  - [ ] Test: SSE streaming (verify events received)
  - [ ] If any fail: Rollback deployment

#### Rollback Strategy

- [ ] Document rollback process
  - [ ] If deployment fails: Revert to previous image
  - [ ] If smoke tests fail: Revert to previous image
  - [ ] Command: `kubectl rollout undo deployment/api`

#### Testing

- [ ] Test: CI/CD pipeline runs
  - [ ] Push commit to main
  - [ ] Verify workflow triggers
  - [ ] Verify tests run
  - [ ] Verify deployment succeeds
- [ ] Test: Smoke tests pass
  - [ ] Verify health checks pass
  - [ ] Verify API calls work
- [ ] Test: Rollback works
  - [ ] Deploy broken code (intentionally)
  - [ ] Verify rollback triggered

**Validation**:
- [ ] CI/CD pipeline works (end-to-end)
- [ ] Smoke tests pass
- [ ] Rollback strategy tested
- [ ] Deployments automated

**Tests**:
```bash
git push origin main
# Watch GitHub Actions workflow
```

---

### Day 97: Production Monitoring Setup

**Value**: Real-time production observability

#### Metrics (Prometheus + Grafana)

- [ ] Deploy Prometheus to Kubernetes
  - [ ] Use Helm chart: `helm install prometheus prometheus-community/prometheus`
  - [ ] Configure scrape targets (API, PostgreSQL, Redis)
- [ ] Deploy Grafana to Kubernetes
  - [ ] Use Helm chart: `helm install grafana grafana/grafana`
  - [ ] Add Prometheus data source
  - [ ] Import dashboards:
    - [ ] API performance (requests/sec, latency, errors)
    - [ ] Deliberation metrics (sessions, cost, rounds)
    - [ ] Infrastructure (CPU, memory, disk)

#### Alerts (Alertmanager)

- [ ] Configure Alertmanager
  - [ ] Alert: API error rate >5% (5 min)
  - [ ] Alert: API latency p95 >1s (5 min)
  - [ ] Alert: Deliberation cost spike >200% (1 hour)
  - [ ] Alert: Database connection pool exhausted
  - [ ] Send to: ntfy.sh (admin alerts)

#### Logs (Loki or CloudWatch)

- [ ] Deploy Loki to Kubernetes (optional for MVP)
  - [ ] Use Helm chart: `helm install loki grafana/loki-stack`
  - [ ] Configure log aggregation (all pods)
  - [ ] Add to Grafana (Loki data source)
- [ ] OR: Use DigitalOcean Monitoring (managed logs)

#### Testing

- [ ] Test: Prometheus scraping metrics
  - [ ] Visit Prometheus UI
  - [ ] Verify targets UP
  - [ ] Query: `http_requests_total`
- [ ] Test: Grafana dashboards render
  - [ ] Visit Grafana UI
  - [ ] Verify dashboards display
  - [ ] Verify data flowing
- [ ] Test: Alerts trigger
  - [ ] Trigger error rate alert (stop API)
  - [ ] Verify alert sent to ntfy.sh

**Validation**:
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards working
- [ ] Alerts configured and tested
- [ ] Logs aggregated (optional)

**Tests**:
Manual testing via Prometheus/Grafana UI

---

### Day 98: Production Data Migration

**Value**: Migrate existing data to production DB

#### Database Migration

- [ ] Export development data
  ```bash
  pg_dump $DEV_DATABASE_URL > dev_data.sql
  ```
- [ ] Review exported data
  - [ ] Remove test users (if any)
  - [ ] Remove test sessions (if desired)
  - [ ] Verify data integrity
- [ ] Import to production
  ```bash
  psql $PROD_DATABASE_URL < dev_data.sql
  ```
- [ ] Verify migration
  - [ ] Count: users, sessions, contributions
  - [ ] Verify: No data loss

#### Stripe Migration (Test → Live)

- [ ] Switch Stripe keys
  - [ ] Update `.env`: `STRIPE_SECRET_KEY=sk_live_xxx`
  - [ ] Update frontend: `VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxx`
  - [ ] Update webhook URL in Stripe dashboard (production)
- [ ] Migrate test subscriptions (if any)
  - [ ] Manually create live subscriptions for existing Pro users
  - [ ] OR: Ask users to re-subscribe (simpler)

#### Testing

- [ ] Test: Production database accessible
  - [ ] Connect to prod DB
  - [ ] Query users, sessions
  - [ ] Verify data correct
- [ ] Test: Stripe live mode works
  - [ ] Complete real checkout (refund immediately)
  - [ ] Verify webhook received
  - [ ] Verify subscription created

**Validation**:
- [ ] Data migrated successfully
- [ ] No data loss
- [ ] Stripe live mode works
- [ ] Webhooks configured correctly

**Tests**:
Manual verification + test checkout

---

### Day 99: Final Security Hardening

**Value**: Production-grade security

#### Security Hardening Checklist

- [ ] Rotate all secrets
  - [ ] Anthropic API key (new key for prod)
  - [ ] Supabase service role key (new key for prod)
  - [ ] Stripe webhook secret (new for prod webhook)
  - [ ] Admin API key (new random UUID)
  - [ ] JWT signing key (Supabase auto-manages)
- [ ] Enable security headers
  - [ ] HSTS: `Strict-Transport-Security: max-age=31536000`
  - [ ] CSP: `Content-Security-Policy: default-src 'self'`
  - [ ] X-Frame-Options: `DENY`
  - [ ] X-Content-Type-Options: `nosniff`
- [ ] Enable rate limiting (strict for production)
  - [ ] Free: 2 sessions/day (stricter than dev)
  - [ ] Pro: 10 sessions/day
  - [ ] Per-IP: 100 requests/min (DDoS protection)
- [ ] Review permissions
  - [ ] PostgreSQL: App user has minimal permissions (SELECT, INSERT, UPDATE only)
  - [ ] Kubernetes: Service accounts have minimal RBAC
  - [ ] DigitalOcean: Admin access limited to 1-2 people

#### Penetration Test (Final)

- [ ] Re-run security audits (Day 86-88)
  - [ ] Auth security
  - [ ] API security
  - [ ] Infrastructure security
- [ ] Verify: All issues from Week 13 resolved

#### Testing

- [ ] Test: Security headers present
  ```bash
  curl -I https://app.boardofone.com
  ```
  - [ ] Verify HSTS header
  - [ ] Verify CSP header
- [ ] Test: Rate limiting works (production)
  - [ ] Make 100+ requests in 1 min
  - [ ] Verify 429 error after 100

**Validation**:
- [ ] All secrets rotated
- [ ] Security headers enabled
- [ ] Rate limiting stricter
- [ ] Permissions reviewed (minimal)
- [ ] Penetration tests pass

**Tests**:
Manual security testing

---

### Day 100: Launch Announcement Preparation

**Value**: Marketing ready for launch

#### Landing Page

- [ ] Create landing page (if not exists)
  - [ ] Hero: "AI-powered deliberation for solopreneurs"
  - [ ] Features: Multi-agent debate, expert personas, consensus building
  - [ ] Pricing: Free, Pro, Enterprise
  - [ ] CTA: "Start Your First Deliberation"
- [ ] Verify SEO
  - [ ] Meta tags (title, description)
  - [ ] Open Graph tags (for social sharing)
  - [ ] Sitemap.xml
  - [ ] Robots.txt

#### Launch Checklist

- [ ] Create launch checklist
  - [ ] Product Hunt launch (optional, post-MVP)
  - [ ] Twitter/X announcement
  - [ ] LinkedIn post
  - [ ] Hacker News Show HN (optional)
  - [ ] Email existing waitlist (if any)
  - [ ] Personal network outreach

#### Demo Video

- [ ] Record demo video (3-5 min)
  - [ ] Show: Create session
  - [ ] Show: Real-time deliberation
  - [ ] Show: Synthesis report
  - [ ] Highlight: Pause/resume, cost transparency
- [ ] Upload to YouTube (unlisted or public)
- [ ] Embed on landing page

#### Testing

- [ ] Test: Landing page loads
  - [ ] Visit https://app.boardofone.com
  - [ ] Verify content correct
  - [ ] Verify CTA works (signup)
- [ ] Test: Demo video works
  - [ ] Verify video plays
  - [ ] Verify no audio issues
- [ ] Test: Social sharing
  - [ ] Share on Twitter
  - [ ] Verify Open Graph image displays

**Validation**:
- [ ] Landing page ready
- [ ] Demo video recorded
- [ ] Launch checklist prepared
- [ ] Social sharing works

**Tests**:
Manual testing

---

### Day 101: Launch Day + Monitoring

**Value**: Go live, monitor closely

#### Pre-Launch Checklist

- [ ] Verify all systems healthy
  - [ ] API health checks: 200 OK
  - [ ] Database: Responding
  - [ ] Redis: Responding
  - [ ] Stripe: Webhooks configured
  - [ ] Resend: Emails delivering
- [ ] Announce launch
  - [ ] Twitter/X post
  - [ ] LinkedIn post
  - [ ] Email waitlist
  - [ ] Show HN (if planned)

#### Launch Monitoring

- [ ] Monitor metrics (first 24 hours)
  - [ ] Active users (count)
  - [ ] Signups (count)
  - [ ] Deliberations created (count)
  - [ ] Error rate (%)
  - [ ] API latency (p95)
  - [ ] Cost per deliberation (avg)
- [ ] Monitor alerts (ntfy.sh)
  - [ ] Watch for runaway sessions
  - [ ] Watch for cost spikes
  - [ ] Watch for system errors
- [ ] Monitor support requests
  - [ ] Check support email (support@boardofone.com)
  - [ ] Respond within 4 hours (SLA for launch day)

#### Celebrate

- [ ] Take a break
- [ ] Celebrate launch with team
- [ ] Reflect on journey (3.5 months of work!)
- [ ] Plan next steps (post-MVP roadmap)

**Validation**:
- [ ] Launch successful (no critical errors)
- [ ] Users signing up
- [ ] Deliberations running smoothly
- [ ] Monitoring working (real-time)

**Tests**:
Live production monitoring

**Deliverables**:
- Launch announcement posts
- Production metrics dashboard

#### Business Continuity & Bus Factor Mitigation

**Value**: Ensure system can operate even if solo founder incapacitated

**Tasks**:
- [ ] Create emergency access credentials vault
  - Setup 1Password shared vault: "Board of One - Emergency"
  - Store all critical credentials:
    - DigitalOcean account (owner)
    - Supabase project (admin)
    - Stripe account (owner)
    - Anthropic API key
    - GitHub repository (admin)
    - Domain registrar (Namecheap/Cloudflare)
    - Email admin (support@boardofone.com)
  - Share vault with trusted person (family member, co-founder, or lawyer)
- [ ] Document emergency contact list
  ```markdown
  # Emergency Contacts

  If solo founder (You) is incapacitated:

  **Primary Contact**: [Name, Phone, Email]
  - Has access to 1Password emergency vault
  - Can access all systems

  **Hosting**: DigitalOcean
  - Account email: [email]
  - Support: support@digitalocean.com

  **Users**: Can contact support@boardofone.com
  - Auto-responder: "Service may be delayed due to emergency"

  **Revenue**: Stripe continues to charge subscriptions
  - Funds accumulate in Stripe account
  - No immediate action needed
  ```
- [ ] Create system shutdown procedure (worst case)
  ```markdown
  # Emergency Shutdown Procedure

  If system must be shut down:

  1. Post status page notice (24-48h advance warning)
  2. Email all users (data export instructions)
  3. Disable new signups
  4. Allow 7 days for data exports
  5. Refund Pro users (pro-rated for unused time)
  6. Archive database backups (keep for 90 days)
  7. Decommission servers
  8. Post final notice with data retrieval instructions
  ```
- [ ] Document system operation knowledge base
  - Architecture overview (how it works)
  - Common operations (restart server, check logs)
  - Emergency procedures (database restore, rollback deploy)
- [ ] Test emergency vault access (have trusted person access and report)

**Validation**:
- [ ] Emergency vault created with all credentials
- [ ] Trusted person confirmed access
- [ ] Documentation complete and reviewed

**Deliverables**:
- 1Password emergency vault (shared)
- docs/BUSINESS_CONTINUITY.md
- docs/EMERGENCY_CONTACTS.md
- docs/SYSTEM_OPERATION_KNOWLEDGE.md

---

## Summary of MVP Implementation Roadmap

**Total Weeks Covered**: 14.5 weeks (Week 3.5 through Week 14)
**Total Days Planned**: 101 days (Days 21-101)
**Total Tasks Estimated**: 1,236 tasks (includes 170 new 10/10 production-grade tasks)
**Estimated Completion Date**:
- Start: 2025-11-14 (Week 3.5, Day 21)
- End: 2026-02-23 (Week 14, Day 101)
- **14.5 weeks from start to MVP launch**

**10/10 Production-Grade Additions** (170 new tasks):
- Week 4 (Day 22-23): Developer onboarding + code review guidelines + troubleshooting (31 tasks)
- Week 9 (Day 61): Vendor outage contingency + cost anomaly detection + feature flags + SLI/SLO/SLA (84 tasks)
- Week 13 (Day 92): Blue-green deployment (20 tasks)
- Week 14 (Day 101): Business continuity planning (35 tasks)

**Key Milestones Achieved**:
1. ✅ **Week 3 Complete**: Console v1 validated (foundation solid)
2. **Week 5 Complete**: Console migrated to LangGraph (unified architecture, infinite loop prevention)
3. **Week 7 Complete**: Web UI with real-time streaming (SSE, pause/resume)
4. **Week 8 Complete**: Payments + emails integrated (Stripe, Resend)
5. **Week 9 Complete**: Production hardening (runaway detection, ntfy.sh, health checks)
6. **Week 11 Complete**: Admin dashboard operational (monitoring, kill switches, cost analytics)
7. **Week 12 Complete**: Email system complete (all templates, unsubscribe flow)
8. **Week 13 Complete**: QA + security audit passed (load testing, GDPR compliance)
9. **Week 14**: Public beta launch 🚀

**Dependencies & Prerequisites**:
- PostgreSQL (Supabase) required starting Week 6
- Stripe test mode throughout development, live mode Week 14
- DigitalOcean account setup Week 14 (Day 92)
- Resend domain verification Week 8 (Day 55)
- ntfy.sh topic created Week 9 (Day 58)

**Critical Path Items** (Must Not Slip):
1. Week 5: LangGraph migration + infinite loop prevention (foundational for all future work)
2. Week 8: Stripe integration (monetization critical for sustainability)
3. Week 9: Production hardening (safety guarantees required before public launch)
4. Week 13: Security audit (must pass before launch)

**Risk Mitigation**:
- **Buffer Days**: Built into each week (typically Day 7 = polish/testing)
- **Go/No-Go Gates**: End of each week has explicit validation criteria
- **Rollback Plans**: CI/CD includes automated rollback (Day 93)
- **Load Testing**: Week 13 ensures system handles production load

**Post-Launch (Week 15+)** (Not in this roadmap):
- User feedback collection
- Bug fixes and hotfixes
- Performance optimizations
- Feature requests prioritization
- Sentry integration (error tracking)
- PostHog integration (product analytics)
- Mobile apps (Phase 2)
- API for integrations (Phase 2)

**Documentation Deliverables**:
Each week produces a summary document:
- `WEEK4_BENCHMARK_RESULTS.md`
- `WEEK5_RETROSPECTIVE.md`
- `WEEK6_API_SUMMARY.md`
- `WEEK8_PAYMENTS_EMAIL_SUMMARY.md`
- `WEEK9_PRODUCTION_HARDENING_SUMMARY.md`
- `ADMIN_DASHBOARD_COMPLETE.md`
- `WEEK12_EMAIL_COMPLETE.md`
- `WEEK13_QA_SECURITY_COMPLETE.md`
- `WEEK13_RETROSPECTIVE.md`

**Final Note**:
This roadmap is comprehensive but flexible. Adjustments will be needed based on:
- Actual implementation challenges
- User feedback during development
- Security audit findings
- Performance bottlenecks discovered during load testing
- Timeline slippage (use buffer days wisely)

The roadmap prioritizes:
1. **Safety** (infinite loop prevention, kill switches)
2. **Security** (audits, GDPR compliance)
3. **User Experience** (real-time streaming, pause/resume)
4. **Observability** (monitoring, alerts, logging)
5. **Sustainability** (payments, cost optimization)

**Ready to Ship**: After Week 14, the system is production-ready with:
- ✅ Unified LangGraph architecture
- ✅ Real-time web UI
- ✅ Stripe payments working
- ✅ Admin monitoring dashboard
- ✅ Production safety guarantees (5-layer loop prevention)
- ✅ Security audited
- ✅ Load tested
- ✅ GDPR compliant
- ✅ Deployed to DigitalOcean
- ✅ Monitored with Prometheus + Grafana + ntfy.sh

**10/10 Production-Grade Features** (What makes this exceptional):
- ✅ **Vendor Resilience**: Graceful degradation when Supabase/Anthropic/Stripe/Resend fail
- ✅ **Cost Controls**: Real-time cost tracking, anomaly detection, auto-pause on budget exceeded
- ✅ **Feature Flags**: Deploy risky features safely with percentage rollout
- ✅ **SLI/SLO/SLA**: Defined service level objectives with error budget tracking
- ✅ **Blue-Green Deployment**: Zero-downtime deploys with instant rollback
- ✅ **Developer Experience**: One-command setup, troubleshooting guide, code review standards
- ✅ **Business Continuity**: Emergency vault, succession plan, graceful shutdown procedure
- ✅ **Operational Excellence**: The system "just works" and you know what to do when it doesn't

**What Makes This 10/10**:
- **9/10 is "it works"** - System functions correctly under normal conditions
- **10/10 is "it works AND we planned for everything"** - Every failure mode has a mitigation plan
- **Zero-surprise production**: No panics, no unexpected bills, no mystery outages
- **Solo founder ready**: Can launch confidently as a single person with minimal operational overhead
- **Sleep soundly**: Monitoring + alerts + runbooks mean emergencies are handled systematically

🚀 **Let's build something amazing!**
