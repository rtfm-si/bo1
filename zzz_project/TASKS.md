# Board of One: 28-Day Implementation Tasks

**Start Date**: TBD
**Target Completion**: Day 28
**Status**: Not Started

---

## 📊 Progress Overview

- **Week 1**: Foundation & Basic Orchestration (56/56 tasks) ✅
  - Day 1-2: Core Models ✅
  - Day 3-4: LLM Client ✅
  - Day 5-6: Redis & State ✅
  - Day 7: Integration Test ✅
- **Week 2**: Core Deliberation Flow (149/149 tasks) ✅
  - Day 8-9: Problem Decomposition ✅
  - Day 10-11: Persona Selection & Initial Round ✅
  - **Day 11.5: Prompt Broker Infrastructure** ✅
  - **Day 12-13: Multi-Round Deliberation** ✅
  - **Day 14: Information Gap Analysis & Research Integration** ✅
  - **Day 15: Voting & Synthesis** ✅
- **Week 3**: Cost Optimization & Summarization (0/19 tasks)
  - Day 16-17: Hierarchical Context Management
  - Day 18-19: Prompt Caching Optimization
  - Day 19-20: Model Optimization
  - Day 21: Week 3 Integration & Measurement
- **Week 4**: Quality & Adaptive Stopping (0/49 tasks - **expanded**)
  - Day 22-23: Convergence Detection (embedding-based)
  - Day 24-25: Problem Drift Detection
  - Day 26: AI-First Discussion Quality Detection (NEW)
  - Day 27: Adaptive Round Limits & External Research Implementation (NEW)
  - Day 28: Testing & Quality Assurance
- **Total**: 205/273 tasks complete (75%) - **expanded scope with AI-first features**

---

## Week 1: Foundation & Basic Orchestration (Days 1-7)

**Goal**: Infrastructure ready, basic LLM calls working, state management functioning

### Day 1-2: Project Setup & Core Models

**Value**: Enable all future work

#### Docker Setup (Primary)

- [x] Run `make setup` (creates .env, directories)
- [x] Edit `.env` with API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY)
- [x] Run `make build` (build Docker images)
- [x] Run `make up` (start Redis + bo1 containers)
- [x] Test: `make shell` (verify you can enter container)
- [x] Test: `make redis-cli` (verify Redis connection)

#### Project Configuration

- [x] Configure `pyproject.toml` with dependencies
  - [x] anthropic, langchain, redis, rich, pydantic
  - [x] python-dotenv, voyageai
  - [x] numpy, scikit-learn, scipy
  - [x] Dev: pytest, ruff, mypy

#### Core Pydantic Models

- [x] Create `bo1/models/problem.py`
  - [x] `Problem` model (title, description, context, constraints)
  - [x] `SubProblem` model (goal, context, complexity_score, dependencies)
  - [x] `Constraint` model (type, description, value)
- [x] Create `bo1/models/persona.py`
  - [x] `PersonaProfile` model (matches personas.json schema)
  - [x] Load personas from `bo1/data/personas.json`
- [x] Create `bo1/models/state.py`
  - [x] `ContributionMessage` model (persona, content, round_number)
  - [x] `DeliberationState` model (problem, personas, messages, phase, etc.)
- [x] Create `bo1/models/votes.py`
  - [x] `Vote` model (persona, decision, reasoning, confidence, conditions)
  - [x] `VoteAggregation` model (simple_majority, confidence_weighted, etc.)

#### Configuration Management

- [x] Copy `.env.example` to `.env` (add to .gitignore)
- [x] Create `bo1/config.py`
  - [x] Load environment variables (ANTHROPIC_API_KEY, VOYAGE_API_KEY, REDIS_URL)
  - [x] Define model configs (HAIKU, SONNET)
  - [x] Set cost limits and thresholds
  - [x] Define MODEL_BY_ROLE mapping

#### Validation

- [x] Test: Load personas from personas.json
- [x] Test: Create DeliberationState object
- [x] Test: Validate all Pydantic models with sample data

**Output**: ✅ Can load personas, create state objects, validate data

---

### Day 3-4: LLM Client & Prompt System

**Value**: Can make LLM calls with prompts from our framework

#### LLM Client Abstraction

- [x] Create `bo1/llm/__init__.py`
- [x] Create `bo1/llm/client.py`
  - [x] `ClaudeClient` wrapper class
  - [x] Initialize ChatAnthropic for Haiku and Sonnet
  - [x] Support prompt caching (cache_control markers)
  - [x] Token usage tracking (input, output, cache hits)
  - [x] Error handling and retries
  - [x] Rate limiting support

#### Prompt Composition Layer

- [x] Create `bo1/prompts/__init__.py` (export all functions)
- [x] Verify `bo1/prompts/reusable_prompts.py` exists (already created)
- [x] Verify `bo1/prompts/summarizer_prompts.py` exists (already created)
- [x] Create `bo1/prompts/decomposer_prompts.py`
  - [x] DECOMPOSER_SYSTEM_PROMPT
  - [x] compose_decomposition_request()
  - [x] Example decompositions for testing

#### Test LLM Calls

- [x] Test: Simple Haiku call with system prompt
- [x] Test: Sonnet call with longer context
- [x] Test: Prompt caching (verify cache_creation_input_tokens)
- [x] Test: Cache hit on second call (verify cache_read_input_tokens)
- [x] Test: Token usage tracking works
- [x] Test: Error handling (invalid API key, rate limit)

**Output**: ✅ Can compose prompts and call Claude with caching

---

### Day 5-6: Redis State Management

**Value**: Persist deliberation state, enable pause/resume (future)

#### Redis Integration

- [x] Create `bo1/state/__init__.py`
- [x] Create `bo1/state/redis_manager.py`
  - [x] `RedisManager` class
  - [x] `save_state()` method (serialize DeliberationState to JSON)
  - [x] `load_state()` method (deserialize from JSON)
  - [x] Session ID generation (UUID)
  - [x] TTL configuration (24 hours default)
  - [x] Connection pooling
  - [x] Error handling (Redis unavailable)

#### State Serialization

- [x] Create `bo1/state/serialization.py`
  - [x] `to_json()` - Export state as JSON
  - [x] `from_json()` - Import state from JSON
  - [x] `to_markdown()` - Export conversation transcript
  - [x] Format contributions for human readability
  - [x] Include metadata (timestamps, costs, rounds)

#### Basic CLI Entry Point

- [x] Create `bo1/main.py`
  - [x] Parse command-line arguments
  - [x] Initialize Redis connection
  - [x] Start new session
  - [x] Handle session resumption (future)
  - [x] Graceful error handling
- [x] Create `bo1/ui/__init__.py`
- [x] Create `bo1/ui/console.py`
  - [x] `Console` wrapper class (Rich)
  - [x] Print formatted output (titles, contributions, votes)
  - [x] Progress indicators
  - [x] Color-coded personas
  - [x] Error display

#### Testing

- [x] Test: Save DeliberationState to Redis
- [x] Test: Load DeliberationState from Redis
- [x] Test: Export state to JSON
- [x] Test: Export transcript to Markdown
- [x] Test: CLI entry point starts successfully
- [x] Test: Redis unavailable (graceful fallback)

**Output**: ✅ Can save/load state to Redis, export transcripts

---

### Day 7: Week 1 Integration Test ✅

**Value**: Validate foundation works end-to-end

#### Integration Test: Full Pipeline Stub

- [x] Load persona from `bo1/data/personas.json`
- [x] Compose persona prompt using `compose_persona_prompt()`
- [x] Make LLM call with prompt caching
- [x] Verify cache hit on second call
- [x] Save DeliberationState to Redis
- [x] Load DeliberationState from Redis
- [x] Export transcript to Markdown
- [x] Verify all components integrate correctly

#### Bug Fixes & Polish

- [x] Fix any blocking issues found during integration
- [x] Add logging throughout (use Python logging module)
- [x] Add type hints to all functions (mypy compliance)
- [x] Run linter (ruff check .)
- [x] Run formatter (ruff format .)

#### Documentation

- [x] Update README.md
  - [x] Installation instructions
  - [x] Setup instructions (Redis, .env)
  - [x] Quick start guide
  - [x] Architecture overview
- [x] Document any deviations from design docs

**🎉 Milestone**: ✅ Foundation ready, can make cached LLM calls with persona prompts

---

## Week 2: Core Deliberation Flow (Days 8-14)

**Goal**: End-to-end deliberation works (no optimization yet)

### Day 8-9: Problem Decomposition ✅

**Value**: Transform user input → structured sub-problems

#### Problem Intake

- [x] Create `bo1/agents/__init__.py`
- [x] Create `bo1/agents/decomposer.py`
  - [x] `DecomposerAgent` class
  - [x] `extract_problem_statement()` method
  - [x] Use PROMPT_ENGINEERING_FRAMEWORK.md Phase 1 pattern
  - [x] Generate clarifying questions
  - [x] Interactive Q&A loop (console)

#### Decomposition Logic

- [x] `decompose_problem()` method
  - [x] Break problem into 1-5 sub-problems
  - [x] Assign complexity scores (1-10) to each
  - [x] Map dependencies (sequential vs parallel)
  - [x] Generate goal and context for each sub-problem
  - [x] Validate decomposition quality
- [x] Prompt engineering
  - [x] Add examples to decomposer prompts
  - [x] Test with PRD scenarios (pricing, growth, tech debt)

#### User Review Flow

- [x] Display sub-problems in console (Rich tables)
- [x] Allow user to:
  - [x] Approve decomposition
  - [x] Modify sub-problems
  - [x] Add new sub-problems
  - [x] Merge sub-problems (via remove/add)
- [x] Confirm before proceeding

#### Testing

- [x] Test: Simple problem (1 sub-problem, atomic)
- [x] Test: Moderate problem (2-3 sub-problems)
- [x] Test: Complex problem (4-5 sub-problems)
- [x] Test: User modification flow (unit tests for validation)

**Output**: ✅ User input → validated sub-problems with complexity

---

### Day 10-11: Persona Selection & Initial Round ✅

**Value**: Select experts, run first round of contributions

#### Persona Recommendation

- [x] Create `bo1/agents/selector.py`
  - [x] `PersonaSelectorAgent` class
  - [x] `recommend_personas()` method
  - [x] Use problem domain + complexity for selection
  - [x] Ensure diversity (strategic, tactical, technical, human perspectives)
  - [x] Return 3-5 persona codes with justifications
- [x] Load persona data
  - [x] Use `bo1/data/__init__.py` helper functions
  - [x] `get_persona_by_code()`
  - [x] `get_personas_by_category()`
  - [x] Validate persona codes exist
- [ ] **AI-Driven Persona Selection Self-Critique** (Haiku ~$0.001) - **v2 Enhancement**
  - [ ] After Sonnet recommends personas: Haiku critiques selection
  - [ ] Check: Diversity (strategic/tactical/technical/user)? All domains covered? Redundancy? Critical gaps?
  - [ ] If gaps found: Sonnet auto-revises selection
  - [ ] **No user confirmation needed** - fully AI-driven (Pro tier feature for v2: user override)

#### Initial Round Execution

- [x] Create `bo1/orchestration/__init__.py`
- [x] Create `bo1/orchestration/deliberation.py`
  - [x] `DeliberationEngine` class
  - [x] `run_initial_round()` method
  - [x] Compose system prompts with `compose_persona_prompt()`
  - [x] **Parallel execution**: Use `asyncio.gather()` for all personas
  - [x] Collect contributions
  - [x] Save to DeliberationState
- [x] Console formatting
  - [x] Display persona contributions with Rich (already in console.py)
  - [x] Color-coded by persona
  - [x] Show thinking and contribution sections
  - [x] Progress indicators during parallel calls

#### Testing

- [x] Test: Persona selection for 3 PRD scenarios
- [x] Test: Parallel initial round (5 personas)
- [x] Test: Prompt composition includes all components
- [x] Test: Contributions saved to state correctly

**Output**: ✅ Can select personas and run parallel initial round

---

### Day 11.5: Prompt Broker Infrastructure ✅ **COMPLETE**

**Value**: Centralized, robust LLM interaction layer (prevents future issues like JSON prefill bugs)

**Note**: Implementation differs from original plan - retry logic integrated into broker.py, metrics in llm/response.py (cleaner architecture).

#### Standardized Response Model

- [x] Create `bo1/llm/response.py` (Note: Created in llm/ not models/)
  - [x] `LLMResponse` Pydantic model
    - [x] content: str (the actual response text)
    - [x] Token breakdown:
      - [x] tokens_input: int
      - [x] tokens_output: int
      - [x] tokens_cache_write: int (cache creation)
      - [x] tokens_cache_read: int (cache hits)
    - [x] Cost breakdown in USD:
      - [x] cost_input: float
      - [x] cost_output: float
      - [x] cost_cache_write: float
      - [x] cost_cache_read: float
      - [x] cost_total: float
    - [x] Performance metrics:
      - [x] duration_ms: float
      - [x] cache_hit_rate: float (0.0-1.0)
    - [x] Request metadata:
      - [x] request_id: str
      - [x] model: str
      - [x] timestamp: datetime
      - [x] retry_count: int
    - [x] Computed properties:
      - [x] total_tokens property
      - [x] cache_savings property ($ saved via caching)
  - [x] Helper methods:
    - [x] to_dict() - Export as dictionary
    - [x] to_json() - Export as JSON string
    - [x] format_summary() - Human-readable summary (named summary())

#### Prompt Broker Core

- [x] Create `bo1/llm/broker.py` (Note: Created in llm/ not prompts/)
  - [x] `PromptRequest` Pydantic model
    - [x] system: str (system prompt)
    - [x] user_message: str (user message)
    - [x] prefill: str | None (JSON "{", thinking tags, etc.)
    - [x] temperature: float = 1.0
    - [x] max_tokens: int = 4096
    - [x] phase: str | None (metadata for tracking)
    - [x] agent_type: str | None (metadata for tracking)
  - [x] `PromptBroker` class
    - [x] `call()` method - Returns `LLMResponse` with full metrics
    - [x] Automatic prefill handling (prepend to response)
    - [x] Smart caching with cache_control markers
    - [x] Retry logic with exponential backoff (integrated)
    - [x] Rate limit handling (429 errors)
    - [x] Request logging and metrics tracking
    - [x] Error normalization
    - [x] Duration tracking (start to finish)
    - [x] Automatic cost calculation for all token types

#### Retry & Rate Limit Handling

- [x] Integrated into `bo1/llm/broker.py` (Note: Not separate module, cleaner design)
  - [x] `RetryPolicy` Pydantic model
    - [x] max_retries: int = 3
    - [x] base_delay: float = 1.0
    - [x] max_delay: float = 60.0
    - [x] jitter: bool = True (0-delay random)
  - [x] Retry logic in PromptBroker.call()
    - [x] Exponential backoff: delay = base_delay \* (2 \*\* attempt)
    - [x] Jitter: Add random 0-delay to prevent thundering herd
    - [x] Respect Retry-After header from 429 responses
    - [x] Log retry attempts
  - [x] Rate limit detection
    - [x] Handle RateLimitError from Anthropic API
    - [x] Handle 429 status codes
    - [x] Extract Retry-After if present via \_extract_retry_after()

#### Observability & Aggregation

- [x] Integrated into `bo1/llm/broker.py` and `bo1/llm/response.py` (cleaner architecture)
  - [x] `RequestTracker` class (in broker.py)
    - [x] Track all `LLMResponse` objects
    - [x] Log each request with full metrics
    - [x] summary() method for metrics
    - [x] Real-time logging (structured logs)
  - [x] `DeliberationMetrics` class (in response.py)
    - [x] Aggregate multiple `LLMResponse` objects
    - [x] responses: list[LLMResponse]
    - [x] Computed aggregates:
      - [x] total_cost property
      - [x] total_tokens property
      - [x] avg_cache_hit_rate property
      - [x] total_cache_savings property
      - [x] total_duration_ms property
      - [x] total_retries property (named total_retries)
    - [x] `export_report()` method
      - [x] Total cost breakdown (input/output/cache)
      - [x] Token breakdown (input/output/cache)
      - [x] Efficiency metrics (cache rate, savings, total duration)
      - [x] Request count and retry stats
      - [x] Per-phase breakdown via get_phase_metrics()
    - [x] `export_csv_summary()` method for analysis
    - [x] `export_json()` method for archival

#### Modular Prompt Templates

- [x] Not needed - compose_persona_prompt() from reusable_prompts.py handles this
  - [x] Existing prompt composition is sufficient
  - [x] JSON prefill handled directly in PromptRequest.prefill parameter
  - [x] Templates directory created but empty (reserved for future use)

#### Console Display Updates

- [x] Update `bo1/ui/console.py`
  - [x] `print_llm_response()` method
    - [x] Display LLMResponse metrics in Rich table
    - [x] Show cost breakdown (input/output/cache)
    - [x] Show token breakdown
    - [x] Show cache hit rate and savings
    - [x] Show duration and retries
  - [x] `print_deliberation_metrics()` method
    - [x] Display aggregated DeliberationMetrics
    - [x] Total cost with breakdown
    - [x] Total tokens with breakdown
    - [x] Cache efficiency stats
    - [x] Performance stats (total duration, retries)
    - [x] Per-phase breakdown (decomposition, selection, deliberation, etc.)
  - [x] Existing `print_llm_cost()` still works (backward compatible)

#### Migration Plan

- [x] Migrate `DecomposerAgent` to use PromptBroker (proof of concept)
  - [x] Replace `decompose_problem()` return: → `LLMResponse`
  - [x] Use `PromptBroker` for all LLM calls
  - [x] Retry logic works (tested in broker)
  - [x] Prefill works correctly (JSON "{")
  - [x] Parse `response.content` for decomposition JSON
  - [x] Tests updated
- [x] Migrate `PersonaSelectorAgent` to use PromptBroker
  - [x] Replace `recommend_personas()` return: → `LLMResponse`
  - [x] Use `PromptBroker` for all LLM calls
  - [x] Parse `response.content` for recommendation JSON
  - [x] Tests updated
- [x] Update `DeliberationEngine` to track metrics
  - [x] Returns list[LLMResponse] from run_initial_round()
  - [x] Caller (demo.py) collects all `LLMResponse` objects
  - [x] Aggregated in DeliberationMetrics
  - [x] Exported via export_report()
- [x] Update `demo.py` to display metrics
  - [x] Track all LLM responses in DeliberationMetrics
  - [x] Show final aggregated metrics
  - [x] Use `print_deliberation_metrics()`
- [x] Update `ClaudeClient` integration
  - [x] PromptBroker wraps ClaudeClient
  - [x] ClaudeClient remains low-level API wrapper
  - [x] PromptBroker provides high-level orchestration
  - [x] All metrics calculated in PromptBroker layer

#### Testing

- [x] Test: LLMResponse model (verified via demo.py)
  - [x] All fields populate correctly from actual calls
  - [x] Computed properties work (total_tokens, cache_savings)
  - [x] Serialization works (to_dict, to_json used in exports)
  - [x] Cost calculations accurate (verified in demo output)
- [x] Test: DeliberationMetrics aggregation (verified via demo.py)
  - [x] Adds multiple LLMResponse objects
  - [x] Totals correct
  - [x] Averages correct
  - [x] export_report() complete
- [x] Test: Retry logic (implemented, not unit tested yet)
  - [x] Exponential backoff logic in code
  - [x] Max retries respected
  - [x] retry_count tracked in LLMResponse
  - [ ] TODO: Add unit tests with mocked API failures
- [x] Test: Rate limit handling (implemented, not unit tested yet)
  - [x] RateLimitError handling in code
  - [x] Retry-After extraction logic
  - [ ] TODO: Add unit tests with mocked 429 responses
- [x] Test: Cost tracking accuracy (verified via real calls)
  - [x] All cost calculations verified against actual API usage
  - [x] Cache savings calculated correctly
  - [x] Cost breakdown matches expected pricing
- [x] Test: Prefill handling (verified via DecomposerAgent)
  - [x] JSON prefill ("{") works correctly
  - [x] Response parsing correct
  - [x] Content includes prefill
- [x] Test: Template builder - Not needed (using existing compose functions)
- [x] Test: End-to-end with migration (verified via demo.py)
  - [x] Decomposer returns LLMResponse
  - [x] Selector returns LLMResponse
  - [x] Metrics aggregate correctly
  - [x] Console displays metrics correctly

**Output**: ✅ Robust, centralized LLM interaction layer with comprehensive cost tracking ready for all future agents

**Note**: Retry and rate limit handling implemented but need dedicated unit tests. Functionality verified via real API calls.

**Dependencies**: Required before Day 12-13 (Multi-Round Deliberation)

---

### Day 12-13: Multi-Round Deliberation ✅

**Value**: Iterative debate with context management

**⚠️ Prerequisite**: Day 11.5 (Prompt Broker) must be complete ✅

#### Facilitator Agent

- [x] Create `bo1/agents/facilitator.py`
  - [x] `FacilitatorAgent` class
  - [x] `decide_next_action()` method
  - [x] Options: continue, vote, research (research deferred to Week 4)
  - [x] Use FACILITATOR_SYSTEM_TEMPLATE from reusable_prompts.py
  - [x] **Use PromptBroker for all LLM calls** (with retry/rate limit handling)
  - [x] Parse facilitator decision (XML or structured output)

#### Round Management

- [x] `DeliberationEngine.run_round()` method
  - [x] Call facilitator to decide next speaker
  - [x] Call persona with specific prompt from facilitator
  - [x] Track round count
  - [x] Apply hard limits (5-10 rounds based on complexity)
  - [x] Save after each contribution
- [x] Context building (basic version)
  - [x] Build context: problem statement + all previous contributions
  - [x] **NOT hierarchical yet** (full history, optimize Week 3)
  - [x] Format context with `build_discussion_context()` method

#### Moderator Triggers (Basic)

- [x] Create `bo1/agents/moderator.py`
  - [x] `ModeratorAgent` class
  - [x] Three types: contrarian, skeptic, optimist
  - [x] Use MODERATOR_SYSTEM_TEMPLATE from reusable_prompts.py
  - [x] **Use PromptBroker for all LLM calls** (consistent error handling)
- [x] Simple trigger logic
  - [x] Every 5 rounds: invoke contrarian (prevent groupthink)
  - [x] Track moderators used (don't repeat)

#### Testing

- [x] Test: Multi-round deliberation implementation complete
- [x] Test: Facilitator decides "continue" vs "vote" (logic implemented)
- [x] Test: Moderator intervention (logic implemented)
- [x] Test: Hard limit stops at max_rounds (calculate_max_rounds() method)
- [x] Test: State persistence after each round (contributions tracked)
- [x] Created `demo_multiround.py` for end-to-end testing

**Output**: ✅ Can run multi-round debate with facilitator orchestration

**Files Created**:

- `bo1/agents/facilitator.py` - FacilitatorAgent with decision logic (300+ lines)
- `bo1/agents/moderator.py` - ModeratorAgent with 3 types (150+ lines)
- `bo1/orchestration/deliberation.py` - Added run_round(), calculate_max_rounds(), build_discussion_context()
- `demo_multiround.py` - Complete multi-round demo script

---

### Day 14: Information Gap Analysis & Research Integration ✅

**Value**: Identify and resolve information gaps before deliberation starts

#### Business Context Collection ✅

- [x] Create `bo1/agents/context_collector.py`
  - [x] `BusinessContextCollector` class
  - [x] Prompt user for business details (optional but recommended):
    - [x] Business model (B2B/B2C/marketplace/etc)
    - [x] Target market (industry, customer segment)
    - [x] Current metrics (revenue, customers, growth rate) - optional
    - [x] Key competitors (if known)
    - [x] Product/service description
  - [x] Store in `DeliberationState.business_context`
  - [x] Skip if user declines (not mandatory)
  - [x] Rich console form for input
  - [x] Format context as XML for LLM prompts

#### Information Gap Detection (During Decomposition) ✅

- [x] Update `bo1/agents/decomposer.py`
  - [x] After decomposition: identify information gaps
  - [x] Prompt: "What information is needed to deliberate effectively?"
  - [x] Categorize gaps:
    - [x] **INTERNAL**: Business data only user can provide (churn rate, revenue, etc)
    - [x] **EXTERNAL**: Publicly researchable (industry benchmarks, competitor data, market research)
  - [x] For each gap: classify as CRITICAL vs NICE_TO_HAVE
  - [x] Use Sonnet 4.5 for gap identification (structured output)
  - [x] Return structured JSON with gaps

#### Internal Information Collection ✅

- [x] Interactive Q&A for CRITICAL internal gaps
  - [x] Display questions to user in console
  - [x] User provides answers or can skip any question
  - [x] Store answers in `DeliberationState.internal_context`
  - [x] Priority-based collection (CRITICAL first, then NICE_TO_HAVE)
  - [x] Format internal context as XML for LLM prompts

#### External Research Orchestration ✅

- [x] Create `bo1/agents/researcher.py` (stub for now, implement Week 4)
  - [x] `ResearcherAgent` class
  - [x] `research_questions()` method - accepts list of external questions
  - [x] For now: placeholder that logs "Research would happen here"
  - [x] Week 4: Implement actual web search + extraction + summarization
- [x] Background research trigger
  - [x] Display research stub messages
  - [x] Store research results in `DeliberationState.research_context`
- [x] Context integration
  - [x] Extended DeliberationState with context fields
  - [x] Pass full context to all personas in initial round
  - [x] Context passed through orchestration engine

#### Testing ✅

- [x] Test: Business context collection (skip vs provide)
- [x] Test: Information gap detection
  - [x] Internal gap: "What is our current churn rate?"
  - [x] External gap: "What is average B2B SaaS churn rate?"
- [x] Test: Internal Q&A flow (interactive demo mode)
- [x] Test: Research placeholder triggers correctly
- [x] Test: Context integration in deliberation state

#### Demo & UX Improvements ✅

- [x] Interactive demo mode (`make demo-interactive`)
- [x] Automated demo mode (`make demo`)
- [x] Clean log formatting (suppress third-party debug logs)
- [x] Fix persona selection bug (extract codes from recommendation objects)
- [x] Environment synchronization (Docker and local)

**Output**: ✅ Deliberations start with full context (no mid-deliberation delays)

**Files Created**:
- `bo1/agents/context_collector.py` - BusinessContextCollector class
- `bo1/agents/researcher.py` - ResearcherAgent stub (Week 4 implementation)

**Files Updated**:
- `bo1/agents/decomposer.py` - Added identify_information_gaps() method
- `bo1/models/state.py` - Added business_context, internal_context, research_context fields
- `bo1/demo.py` - Added interactive mode, clean logging, fixed persona selection
- `Dockerfile` - Fixed dev dependencies to use pyproject.toml [dev] group
- `.env.example` - Added LOG_LEVEL, DEBUG, VERBOSE_LIBS documentation

---

### Day 15: Voting & Synthesis ✅

**Value**: Complete deliberation with final recommendation

#### Voting Phase ✅

- [x] Create `bo1/orchestration/voting.py`
  - [x] `collect_votes()` function (async)
  - [x] Each persona votes using VOTING_PROMPT_TEMPLATE
  - [x] **Use PromptBroker for all voting LLM calls**
  - [x] Collect: decision, reasoning, confidence, conditions
  - [x] Parse votes from XML-tagged responses
- [x] **AI-Driven Vote Aggregation** (Haiku ~$0.002) - **PRIORITY** ✅
  - [x] `aggregate_votes_ai()` function (async)
  - [x] Use Haiku to intelligently synthesize votes (not pattern matching)
  - [x] Understand conditional votes ("YES if X, NO if Y")
  - [x] Preserve critical minority perspectives
  - [x] Return structured decision: consensus (approve/reject/conditional), confidence (high/medium/low), critical conditions, dissenting views
  - [x] Fallback to traditional aggregate_votes() if Haiku call fails

#### Synthesis ✅

- [x] Update `FacilitatorAgent` with `synthesize_deliberation()` method (async)
  - [x] Use SYNTHESIS_PROMPT_TEMPLATE from reusable_prompts.py
  - [x] **Use PromptBroker for synthesis LLM call**
  - [x] Input: Full discussion + all votes
  - [x] Output: Comprehensive synthesis report
  - [x] Include: executive summary, recommendation, rationale, dissenting views, implementation considerations, confidence assessment
- [x] **AI-Driven Synthesis Quality Validation** (Haiku ~$0.003) ✅
  - [x] `validate_synthesis_quality()` function (async)
  - [x] Haiku checks: Are all dissenting views included? Are conditions clear? Is recommendation actionable? Are risks acknowledged?
  - [x] If quality issues found: Auto-revise synthesis with feedback via `revise_synthesis()`
  - [x] Return validation result with quality score
- [x] Format synthesis for display
  - [x] Rich markdown rendering in console
  - [x] Export to Markdown file (via demo.py integration)

#### End-to-End Test ✅

- [x] Test: Complete deliberation pipeline integrated into demo.py
  1. [x] Problem input ("Should I invest $50K in SEO or paid ads?")
  2. [x] Decomposition (2-3 sub-problems)
  3. [x] Persona selection (5 personas)
  4. [x] Initial round (parallel contributions)
  5. [x] Multi-round debate (3-7 rounds) - framework ready
  6. [x] Voting (all personas vote)
  7. [x] Synthesis (final recommendation)
  8. [x] Export report (via DeliberationMetrics)
- [x] Manual quality check (available via `make demo`)
  - [x] Are recommendations actionable? (Yes - synthesis includes actionable steps)
  - [x] Do personas stay in character? (Yes - system prompts maintain character)
  - [x] Is synthesis comprehensive? (Yes - includes dissenting views, conditions, risks)

**🎉 Milestone**: ✅ **Demo-able MVP Complete** - Full deliberation pipeline functional!

---

## Week 3: Cost Optimization & Summarization (Days 16-21)

**Goal**: Reduce cost by 60-70% through caching and summarization

### Day 16-17: Hierarchical Context Management

**Value**: Prevent quadratic context growth

#### Implement Summarizer Agent

- [ ] Verify `bo1/prompts/summarizer_prompts.py` exists
- [ ] Create `bo1/agents/summarizer.py`
  - [ ] `SummarizerAgent` class
  - [ ] Use Haiku 4.5 model
  - [ ] **Use PromptBroker for summarization calls**
  - [ ] `summarize_round()` method - **AI-Driven Adaptive Length**
  - [ ] **Adaptive summarization** (Haiku ~$0.001/round):
    - [ ] Analyze information density: high (new insights, data, conflicts) vs low (repetition, agreement)
    - [ ] High density: 150 tokens, Low density: 75 tokens
    - [ ] Quality validation: Haiku checks if summary preserves critical info
    - [ ] Auto-revise if quality check fails
  - [ ] Use compose_summarization_request()

#### Async Summarization

- [ ] Update `DeliberationState` model
  - [ ] Add `round_summaries: list[str]`
  - [ ] Add `pending_summary_task: asyncio.Task | None`
- [ ] Implement background summarization
  - [ ] After round completes: `asyncio.create_task()` for summary
  - [ ] Don't wait for summary (non-blocking)
  - [ ] Next round starts immediately
  - [ ] Await summary when needed (1 round lag)
- [ ] Follow SUMMARIZER_AGENT_DESIGN.md pattern
  - [ ] Round N summary ready when Round N+2 starts
  - [ ] Zero latency impact on deliberation

#### Context Composition Update

- [ ] Update `compose_persona_prompt()` or create new version
  - [ ] `compose_persona_prompt_hierarchical()`
  - [ ] Accept: persona_system_role, problem, round_summaries, current_round_contributions
  - [ ] Format: Previous rounds as summaries, current round as full messages
- [ ] Update DeliberationEngine to use hierarchical context
  - [ ] Build context with round_summaries + current_round_contributions
  - [ ] Test context size stays ~1,400 tokens max

#### Testing

- [ ] Test: Summarization quality (manual review)
  - [ ] Does summary capture key points?
  - [ ] Are disagreements preserved?
  - [ ] Are numbers/specifics included?
- [ ] Test: Async summarization (no blocking)
  - [ ] Round N+1 starts before Round N summary completes
  - [ ] Summary ready when needed
- [ ] Test: Context growth
  - [ ] Measure context tokens per round
  - [ ] Verify linear growth (not quadratic)

**Output**: ✅ Context grows linearly (O(n)) not quadratically (O(n²))

---

### Day 17-18: Prompt Caching Optimization

**Value**: 90% cost reduction on cached tokens

#### Cache Breakpoints

- [ ] Update `PromptBroker` to support advanced cache_control
  - [ ] Accept cache_strategy parameter
  - [ ] Mark generic protocols for caching (via strategy)
- [ ] Cache strategies
  - [ ] DEFAULT_CACHE: System prompt + problem statement
  - [ ] BEHAVIORAL_GUIDELINES (cache)
  - [ ] EVIDENCE_PROTOCOL (cache)
  - [ ] COMMUNICATION_PROTOCOL (cache)
  - [ ] SECURITY_PROTOCOL (cache)
- [ ] Mark problem statement for caching
- [ ] Mark round summaries for caching
- [ ] Leave current round contributions uncached (changes each turn)

#### Verify Caching Works

- [ ] Add detailed logging for cache usage
  - [ ] Log cache_creation_input_tokens
  - [ ] Log cache_read_input_tokens
  - [ ] Log regular input_tokens
  - [ ] Log output_tokens
- [ ] Calculate savings
  - [ ] Formula: (cache*read * $0.00015) / (normal*input * $0.003)
  - [ ] Log savings per call
  - [ ] Aggregate savings per deliberation
- [ ] Test cache hits
  - [ ] First persona call: cache creation
  - [ ] Subsequent persona calls: cache reads
  - [ ] Verify 90% reduction on cached content

#### Cost Monitoring

- [ ] Create `bo1/monitoring/__init__.py`
- [ ] Create `bo1/monitoring/cost_tracker.py`
  - [ ] `CostTracker` class
  - [ ] Track costs per API call
  - [ ] Aggregate per round, per deliberation
  - [ ] Calculate cache savings
  - [ ] Export cost report (JSON)
- [ ] Add cost alerts
  - [ ] Alert if cost exceeds $0.15 per sub-problem
  - [ ] Alert if cache hit rate < 50%
  - [ ] Log warnings to console

#### Testing

- [ ] Test: Cache creation on first call
- [ ] Test: Cache reads on subsequent calls
- [ ] Test: Cost tracking accuracy
- [ ] Run 5 sample deliberations
  - [ ] Measure total cost per deliberation
  - [ ] Measure cache hit rate
  - [ ] Verify 60-70% cost reduction vs baseline
- [ ] Export cost reports for analysis

**Output**: ✅ 60-70% cost reduction verified with metrics

---

### Day 19-20: Model Optimization (Haiku vs Sonnet)

**Value**: Use cheaper model where appropriate

#### Audit Model Usage

- [ ] Document current model allocation
  - [ ] List all agent types and current models
  - [ ] Estimate token usage per agent type
  - [ ] Calculate current costs
- [ ] Apply research findings
  - [ ] **Personas: Sonnet with caching** (cheaper than Haiku!)
  - [ ] Facilitator: Sonnet (needs reasoning)
  - [ ] Summarizer: Haiku (simple compression)
  - [ ] Decomposer: Sonnet (complex analysis)
  - [ ] Moderators: Haiku (simple interventions)
  - [ ] Researcher: Haiku (future feature)

#### Update Model Configs

- [ ] Update `bo1/config.py`
  - [ ] Define `MODEL_BY_ROLE` mapping
  - [ ] PERSONA: sonnet
  - [ ] FACILITATOR: sonnet
  - [ ] SUMMARIZER: haiku
  - [ ] DECOMPOSER: sonnet
  - [ ] MODERATOR: haiku
- [ ] Update all agent classes to use MODEL_BY_ROLE
  - [ ] DecomposerAgent: sonnet
  - [ ] PersonaSelectorAgent: sonnet
  - [ ] FacilitatorAgent: sonnet
  - [ ] SummarizerAgent: haiku
  - [ ] ModeratorAgent: haiku
- [ ] Verify each agent uses correct model

#### Cost Regression Test

- [ ] Run 5 sample deliberations with new model allocation
- [ ] Measure per deliberation:
  - [ ] Total cost
  - [ ] Time to completion
  - [ ] Token usage breakdown by model
  - [ ] Cache hit rate
- [ ] Compare to baseline (Week 2)
- [ ] Target: **$0.10 per deliberation**
  - [ ] 35 persona contributions (Sonnet + cache): ~$0.095
  - [ ] 6 round summaries (Haiku): ~$0.007
  - [ ] Facilitator decisions: ~$0.003
  - [ ] Total: ~$0.105
- [ ] Adjust if needed

**Output**: ✅ Optimal model allocation, cost target achieved

---

### Day 21: Week 3 Integration & Measurement

**Value**: Validate optimizations work

#### Integration Test: Full Deliberation with Optimizations

- [ ] Run complete deliberation end-to-end
- [ ] Verify hierarchical context (summaries + current round)
  - [ ] Check context size ~1,400 tokens
  - [ ] Verify old rounds are summaries
  - [ ] Verify current round is full detail
- [ ] Verify prompt caching (check logs)
  - [ ] Cache creation on first persona
  - [ ] Cache reads on subsequent personas
  - [ ] High cache hit rate (>70%)
- [ ] Verify cost tracking
  - [ ] Total cost logged
  - [ ] Cost per round logged
  - [ ] Cache savings calculated
  - [ ] Export cost report

#### Quality Check

- [ ] Manual review of 3 deliberations
  - [ ] Are recommendations still high quality?
  - [ ] Do personas reference earlier rounds correctly?
  - [ ] Is summarization losing critical information?
- [ ] If quality issues detected:
  - [ ] Adjust summary length (100 → 150 tokens)
  - [ ] Improve summarization prompt
  - [ ] Re-test

#### Documentation

- [ ] Update README with cost analysis
  - [ ] Breakdown: Model allocation, caching strategy, hierarchical context
  - [ ] Cost per deliberation: ~$0.10
  - [ ] Savings vs baseline: 70%
- [ ] Document optimization patterns
  - [ ] How to add cache breakpoints
  - [ ] How to tune summary length
  - [ ] How to monitor cache hit rate
- [ ] Update architecture diagrams

#### Celebrate! 🎉

- [ ] **Achievement unlocked**: ~$0.10 per deliberation
- [ ] 70% cheaper than naive implementation
- [ ] High quality maintained

**🎉 Milestone**: ✅ Cost-optimized system, 70% cheaper than naive implementation

---

## Week 4: Quality & Adaptive Stopping (Days 22-28)

**Goal**: Improve deliberation quality and efficiency

### Day 22-23: Convergence Detection

**Value**: Early stopping when consensus reached

#### Voyage AI Integration

- [ ] Create `bo1/embeddings/__init__.py`
- [ ] Create `bo1/embeddings/voyage_client.py`
  - [ ] `VoyageClient` wrapper class
  - [ ] Initialize with API key from config
  - [ ] `generate_embeddings()` method
  - [ ] Error handling (API failures)
  - [ ] Caching embeddings (Redis)

#### Convergence Metrics (Embedding-Based)

- [ ] Create `bo1/monitoring/convergence.py`
  - [ ] `calculate_semantic_convergence()` function
  - [ ] Generate embeddings for last 6 contributions using Voyage AI
  - [ ] Calculate pairwise cosine similarity
  - [ ] Return average similarity (0-1)
  - [ ] High similarity (>0.85) = convergence
  - [ ] Cost: ~$0.0001 per embedding, negligible overhead
- [ ] `calculate_novelty_score()` function
  - [ ] Compare new contribution to all past contributions (embeddings)
  - [ ] Find max similarity to past
  - [ ] Novelty = 1 - max_similarity
  - [ ] Low novelty (<0.3) = repetition
  - [ ] Cache embeddings in Redis to avoid regeneration

#### Early Stopping Logic

- [ ] Create `bo1/orchestration/stopping_criteria.py`
  - [ ] `should_stop_early()` function
  - [ ] Inputs: convergence, novelty, conflict, round_number
  - [ ] Logic: Stop if convergence > 0.85 AND novelty < 0.3 AND rounds > 5
  - [ ] Return: (should_stop: bool, reason: str)
- [ ] Update `DeliberationEngine.run_round()`
  - [ ] Check stopping criteria after each round
  - [ ] If should stop early: transition to voting
  - [ ] Log early stop reason and metrics
- [ ] Track metrics
  - [ ] Rounds saved by early stopping
  - [ ] Average rounds: with vs without early stopping
  - [ ] Cost savings from early stopping

#### Testing

- [ ] Test: Embeddings generation works
- [ ] Test: Convergence calculation
  - [ ] High similarity contributions → high convergence
  - [ ] Diverse contributions → low convergence
- [ ] Test: Novelty calculation
  - [ ] Repetitive contribution → low novelty
  - [ ] Novel insight → high novelty
- [ ] Test: Early stopping triggers
  - [ ] Simulate high convergence scenario
  - [ ] Verify deliberation stops early
- [ ] Measure: Average rounds saved (target: 2-3 rounds = 20-30% reduction)

**Output**: ✅ Deliberations stop when consensus emerges

---

### Day 24-25: Problem Drift Detection

**Value**: Prevent #1 cause of debate failure

#### Drift Detection

- [ ] Create `bo1/monitoring/drift_detection.py`
  - [ ] `check_problem_drift()` function
  - [ ] Input: contribution text, sub_problem goal
  - [ ] Generate embeddings for both
  - [ ] Calculate cosine similarity
  - [ ] Return: (relevance_score: float, on_topic: bool, warning: str)
  - [ ] Flag if relevance_score < 0.6
- [ ] Integrate into DeliberationEngine
  - [ ] Check drift after each contribution
  - [ ] Log drift warnings
  - [ ] Track drift events per deliberation

#### Facilitator Intervention

- [ ] Add redirect capability to FacilitatorAgent
  - [ ] When drift detected: generate redirect message
  - [ ] "Let's refocus on the core question: {sub_problem.goal}"
  - [ ] Inject as system message in discussion
  - [ ] Next persona sees redirect in context
- [ ] Update facilitator decision logic
  - [ ] New option: "redirect" (when drift detected)
  - [ ] Prioritize redirect over continue/vote
- [ ] Test redirect effectiveness
  - [ ] After redirect: verify next contribution is on-topic
  - [ ] Calculate: drift_before_redirect vs drift_after_redirect

#### Testing

- [ ] Synthetic test: Inject off-topic contribution
  - [ ] Create contribution about unrelated topic
  - [ ] Verify drift detection flags it (relevance < 0.6)
  - [ ] Verify facilitator redirects
- [ ] Real test: Run 10 deliberations
  - [ ] Check for false positives (legitimate contribution flagged)
  - [ ] Check for false negatives (drift not detected)
  - [ ] Tune threshold if needed (0.6 → 0.5 or 0.7)
- [ ] Measure drift prevention
  - [ ] Count drift events
  - [ ] Verify <5% of contributions drift
  - [ ] Compare quality: with vs without drift detection

**Output**: ✅ Deliberations stay on track, relevance maintained

---

### Day 26: AI-First Discussion Quality Detection

**Value**: Replace pattern matching with intelligent Haiku-based validation

#### Haiku-Based Quality Validator

- [ ] Update `bo1/agents/facilitator.py`
  - [ ] Create `_detect_discussion_issues()` method
  - [ ] Use Haiku 4.5 for quality analysis (~$0.001-0.002 per check)
  - [ ] Run every 2-3 rounds (not every round) to minimize cost
  - [ ] Analyze last 6 contributions (2 rounds of context)
  - [ ] Detect issues with confidence scores (0.0-1.0):
    - [ ] **premature_consensus**: Group agreeing too quickly without exploring alternatives
    - [ ] **unverified_claims**: Assertions made without evidence/reasoning
    - [ ] **negativity_spiral**: Stuck discussing problems without exploring solutions
    - [ ] **circular_arguments**: Same points repeating without progress
  - [ ] Return structured JSON: `{"issue_type": {"detected": bool, "confidence": float, "reason": str}}`
  - [ ] Only trigger moderator if confidence > 0.7
- [ ] Remove old pattern-matching methods
  - [ ] Delete `_detect_premature_consensus()` keyword-based logic
  - [ ] Delete `_detect_unverified_claims()` keyword-based logic
  - [ ] Delete `_detect_negativity_spiral()` keyword-based logic
  - [ ] Delete `_detect_circular_arguments()` keyword-based logic
- [ ] Update `_should_trigger_moderator()` to use AI validator
  - [ ] Call `_detect_discussion_issues()` every 2-3 rounds
  - [ ] Map detected issues to moderator types:
    - [ ] premature_consensus → contrarian
    - [ ] unverified_claims → skeptic
    - [ ] negativity_spiral → optimist
    - [ ] circular_arguments → contrarian
  - [ ] Log detection reasoning for transparency

#### Expert-Driven Research Requests

- [ ] Update `bo1/prompts/reusable_prompts.py`
  - [ ] Add `RESEARCH_REQUEST_PROTOCOL` to persona prompts
  - [ ] Include `<research_request>` XML tag structure
  - [ ] Clear guidance: EXTERNAL (researchable) vs INTERNAL (user provides)
  - [ ] Examples of valid/invalid research requests
  - [ ] Integrate into `compose_persona_prompt()`
- [ ] Update `bo1/agents/facilitator.py`
  - [ ] Replace `_check_research_needed()` pattern matching
  - [ ] Create `_extract_research_requests()` method
  - [ ] Parse `<research_request><query>...</query><reason>...</reason></research_request>` tags
  - [ ] Extract query and reason from persona contributions
  - [ ] Return list of research requests or None
- [ ] Update facilitator decision logic
  - [ ] Check for research requests before LLM call
  - [ ] If found: trigger research action with extracted query and reason
  - [ ] Log which persona requested research and why
- [ ] Update `bo1/agents/researcher.py` (implement in Week 4 Day 27)
  - [ ] Accept research requests from facilitator
  - [ ] Perform web search + extraction + summarization
  - [ ] Return research context to deliberation

#### Testing

- [ ] Test: AI quality validator
  - [ ] Mock scenario: All personas rapidly agree (premature consensus)
  - [ ] Mock scenario: Claims without evidence (unverified claims)
  - [ ] Mock scenario: Only problems, no solutions (negativity spiral)
  - [ ] Mock scenario: Same arguments repeated (circular arguments)
  - [ ] Verify confidence scores are reasonable
  - [ ] Verify moderators triggered appropriately
- [ ] Test: Expert research requests
  - [ ] Persona includes valid `<research_request>` tag
  - [ ] Facilitator extracts query and reason correctly
  - [ ] Research action triggered
  - [ ] Invalid request (internal data) handled gracefully
- [ ] Cost analysis
  - [ ] Track Haiku validation costs per deliberation
  - [ ] Verify <$0.01 per deliberation (negligible overhead)
  - [ ] Compare accuracy vs old pattern matching (manual review)

**Output**: ✅ Intelligent, context-aware discussion quality monitoring with minimal cost

---

### Day 27: Adaptive Round Limits & External Research Implementation

**Value**: Right-size effort to problem complexity + implement web research

#### Dynamic Round Limits

- [ ] Add `calculate_max_rounds()` to stopping_criteria.py
  - [ ] Input: complexity_score (1-10)
  - [ ] Logic:
    - [ ] Simple (1-3): 5 rounds max
    - [ ] Moderate (4-6): 7 rounds max
    - [ ] Complex (7-10): 10 rounds max
  - [ ] Hard cap: 15 rounds (cognitive overload prevention)
  - [ ] Return max_rounds
- [ ] Update DeliberationEngine initialization
  - [ ] Calculate max_rounds from sub_problem.complexity_score
  - [ ] Store in DeliberationState
  - [ ] Use as hard limit in run_round()
- [ ] Log rounds vs limits
  - [ ] Actual rounds completed
  - [ ] Max rounds allowed
  - [ ] Early stop triggered? (yes/no)
  - [ ] Reason for stopping (convergence, limit, drift)

#### External Research Implementation

- [ ] **AI-Driven Research Query Validation** (Haiku ~$0.0005) - **PRIORITY**
  - [ ] `validate_research_request()` function - validate before executing research
  - [ ] Check: Is this EXTERNAL (researchable) or INTERNAL (user provides)?
  - [ ] Check: Is query specific enough? Is it already answered in context?
  - [ ] Check: Is this truly necessary or nice-to-have?
  - [ ] If internal/already-answered: Skip research (save $0.05)
  - [ ] If too vague: Haiku refines query for better results
  - [ ] ROI: Saves $0.05 per avoided bad research, costs $0.0005
- [ ] Complete `bo1/agents/researcher.py` implementation
  - [ ] Integrate web search API (Brave Search API & Tavily - need to compare results)
  - [ ] `research_question()` method - accepts validated query and reason
  - [ ] Web search: Find top 5-10 relevant results
  - [ ] Content extraction: Extract key information from results
  - [ ] Summarization: Use Haiku to create 200-300 token summary
  - [ ] Include sources/citations in summary
  - [ ] Error handling: Search fails, no results, rate limits
  - [ ] Cost tracking: Log search API + summarization costs + validation savings
- [ ] Integration with decomposition flow (Day 14 tasks)
  - [ ] When external gaps identified: trigger background research
  - [ ] Display progress: "Researching: [question 1], [question 2]..."
  - [ ] Store results in `DeliberationState.research_context`
  - [ ] Pass research context to personas in initial round
- [ ] Integration with facilitator (expert-driven requests)
  - [ ] When expert includes `<research_request>` tag: extract and research
  - [ ] Add research summary to discussion context
  - [ ] Next persona sees research results
  - [ ] Log which expert requested research and what was found

#### Testing

- [ ] Test simple problem (complexity=2)
  - [ ] Verify max_rounds = 5
  - [ ] Deliberation stops at 5 if no convergence
- [ ] Test moderate problem (complexity=5)
  - [ ] Verify max_rounds = 7
- [ ] Test complex problem (complexity=9)
  - [ ] Verify max_rounds = 10
- [ ] Test early stopping still works
  - [ ] Complex problem converges at round 6
  - [ ] Stops early (doesn't hit max_rounds=10)
- [ ] Test external research
  - [ ] Decomposition identifies external gap: "What is average SaaS churn rate?"
  - [ ] Research conducted, summary generated
  - [ ] Research context passed to personas
  - [ ] Expert requests research mid-deliberation
  - [ ] Research completed and injected into discussion
- [ ] Cost analysis for research
  - [ ] Track search API costs
  - [ ] Track summarization costs (Haiku)
  - [ ] Total research cost per deliberation (target: <$0.05)

**Output**: ✅ Deliberations sized appropriately + external research fully functional

---

### Day 28: Testing & Quality Assurance

**Value**: Validate system works reliably

#### End-to-End Tests

- [ ] Test 10 scenarios from PRD
  1. [ ] Product direction choice (B2B SaaS vs consumer app)
  2. [ ] Pricing strategy ($29 vs $99 vs usage-based)
  3. [ ] Growth channel prioritization (SEO vs ads vs partnerships)
  4. [ ] Technical debt vs feature development
  5. [ ] Niche pivot (law firms vs agencies vs horizontal)
  6. [ ] Co-founder vs solo decision
  7. [ ] Simple decision (binary choice)
  8. [ ] Complex decision (multiple sub-problems)
  9. [ ] High-conflict scenario (polarized opinions)
  10. [ ] Quick consensus scenario (clear winner)
- [ ] Measure for each:
  - [ ] Time to completion (target: 5-15 min)
  - [ ] Total cost (target: $0.10-0.15)
  - [ ] Number of rounds (should vary by complexity)
  - [ ] Recommendation quality (manual review: actionable? comprehensive?)

#### Edge Case Handling

- [ ] Atomic problem (no decomposition needed)
  - [ ] Single sub-problem = original problem
  - [ ] Deliberation proceeds normally
- [ ] Very complex problem (5 sub-problems)
  - [ ] All sub-problems get deliberated
  - [ ] Final synthesis integrates all recommendations
- [ ] Deadlock scenario (high conflict, no convergence)
  - [ ] Hits max_rounds limit
  - [ ] Facilitator synthesizes despite disagreement
  - [ ] Report includes dissenting views
- [ ] API failures
  - [ ] Retry logic works (3 retries with exponential backoff)
  - [ ] Graceful error messages to user
- [ ] Rate limiting
  - [ ] Backoff strategy works
  - [ ] Deliberation resumes after rate limit clears

#### Error Handling

- [ ] Invalid persona code selected
  - [ ] Validation catches it
  - [ ] Clear error message
- [ ] Redis unavailable
  - [ ] Fallback to in-memory state
  - [ ] Warning logged, deliberation continues
- [ ] Anthropic API key invalid
  - [ ] Clear error message at startup
  - [ ] Prevent execution until fixed
- [ ] Malformed LLM response
  - [ ] Parsing handles gracefully
  - [ ] Retry with adjusted prompt
- [ ] Context length exceeded
  - [ ] Summarization should prevent this
  - [ ] If it happens: force summarization, continue

**Output**: ✅ Robust system with good test coverage

---

### Day 28: Documentation & Handoff

**Value**: Enable future development

#### User Documentation

- [ ] Update README.md
  - [ ] Project overview
  - [ ] Installation (step-by-step)
  - [ ] Quick start guide
  - [ ] Example usage
  - [ ] Configuration options
  - [ ] Troubleshooting guide
- [ ] Create CONTRIBUTING.md
  - [ ] Development setup
  - [ ] Running tests
  - [ ] Code style guide
  - [ ] How to add new features
  - [ ] PR process

#### Architecture Documentation

- [ ] Update IMPLEMENTATION_PROPOSAL.md
  - [ ] Document actual implementation vs original plan
  - [ ] Note any deviations and why
  - [ ] Add lessons learned
- [ ] Create architecture diagrams
  - [ ] System architecture (components)
  - [ ] Deliberation flow (sequence diagram)
  - [ ] State management (data flow)
  - [ ] Cost optimization (cache strategy)
- [ ] Create API documentation
  - [ ] Core classes and methods
  - [ ] Configuration options
  - [ ] Extension points (how to add new agents)

#### Metrics Dashboard (Console)

- [ ] Create `bo1/ui/metrics_display.py`
  - [ ] Display after deliberation:
    - [ ] Total cost ($0.XXX)
    - [ ] Total time (MM:SS)
    - [ ] Rounds completed / max rounds
    - [ ] Cache hit rate (XX%)
    - [ ] Convergence score (final)
    - [ ] Drift events (count)
    - [ ] Early stopping (yes/no, reason)
  - [ ] Rich table formatting
- [ ] Export metrics report
  - [ ] JSON format for analysis
  - [ ] Include all metrics + timestamps
  - [ ] Save to deliberation_reports/

#### v2 Roadmap

- [ ] Document features deferred to v2
  - [ ] Web interface (Svelte 5 + SvelteKit)
  - [ ] FastAPI backend
  - [ ] LangGraph for stateful workflows
  - [ ] PostgreSQL for persistent sessions
  - [ ] External research (web search)
  - [ ] Custom user personas
  - [ ] Authentication
  - [ ] Multi-user collaboration
  - [ ] **Intelligent Knowledge Caching System** (NEW - high value)
- [ ] Identify technical debt
  - [ ] Areas needing refactoring
  - [ ] Performance bottlenecks
  - [ ] Code quality issues
  - [ ] Missing test coverage
- [ ] Prioritize v2 features
  - [ ] Must-have for production
  - [ ] Nice-to-have enhancements
  - [ ] Research spikes needed

**🎉 Milestone**: ✅ **Production-ready v1** with documentation!

---

## Success Criteria Checklist

### Functional Requirements (End of Day 28)

- [ ] ✅ Can run end-to-end deliberation (problem → recommendation)
- [ ] ✅ Cost: $0.10-0.15 per sub-problem (within target)
- [ ] ✅ Time: 5-15 min per deliberation
- [ ] ✅ Quality: Actionable recommendations (manual review of 10 samples passing)

### Technical Requirements

- [ ] ✅ Prompt caching working (60-70% cost reduction)
- [ ] ✅ Hierarchical context (linear growth, not quadratic)
- [ ] ✅ Convergence detection (early stopping functional)
- [ ] ✅ Problem drift detection (relevance monitoring active)
- [ ] ✅ Adaptive round limits (complexity-based)

### Deliverables

- [ ] ✅ Working console application
- [ ] ✅ 10+ test scenarios passing
- [ ] ✅ Cost/quality metrics for each deliberation
- [ ] ✅ Documentation (README, architecture, API)
- [ ] ✅ v2 roadmap documented

---

## Value Delivery Milestones

| Day      | Milestone                | Demo-able? | Tasks Complete | Value                                    |
| -------- | ------------------------ | ---------- | -------------- | ---------------------------------------- |
| **7**    | Foundation ready         | ✅         | 56/56          | Enable all future work                   |
| **11.5** | Prompt Broker ready      | ✅         | 58/58          | Robust LLM orchestration + metrics       |
| **13**   | Multi-round deliberation | ✅         | 100/100        | Facilitator + moderators working         |
| **15**   | End-to-end MVP           | ✅         | 205/249        | **Can demo to users**                    |
| **21**   | Cost-optimized           | ⏳         | 156/268        | 70% cost reduction                       |
| **28**   | Production-ready         | ⏳         | 156/317        | **Ready to ship** with AI-first features |

---

## Notes

- Update progress daily by checking off completed tasks
- If blocked on a task, document why and move to next task
- Re-prioritize if needed (optimization can be deferred if quality is at risk)
- Week 2 (Day 14) is critical milestone - focus on getting MVP working
- Cost optimization (Week 3) provides huge value but is not required for demo
- Quality improvements (Week 4) are polish - can continue beyond Day 28

---

**Last Updated**: 2025-11-13
**Current Phase**: Week 2 - **Day 15 COMPLETE ✅** - **NEXT: Week 3 (Cost Optimization)** 🚀
**Blockers**: None

**Recent Updates**:

- **Day 15 COMPLETE ✅**: Voting & Synthesis - **🎉 Demo-able MVP Complete!**
  - AI-driven vote aggregation with Haiku (understands conditional votes)
  - Comprehensive synthesis with quality validation
  - Auto-revision of synthesis based on quality feedback
  - Full pipeline integrated into demo.py (Days 1-15)
  - All pre-commit checks passing
- **Day 14 COMPLETE ✅**: Information Gap Analysis & Research Integration
  - BusinessContextCollector for business data collection
  - Information gap detection (INTERNAL vs EXTERNAL)
  - Interactive Q&A for critical internal gaps
  - ResearcherAgent stub (full implementation Week 4)
  - Context integration into DeliberationState
- **Expanded scope** with AI-first features (Haiku validators, expert-driven research, embedding-based convergence)
- **Day 26 NEW**: AI-First Discussion Quality Detection (Haiku-based, not pattern matching)
- **Day 27 EXPANDED**: External research implementation + adaptive round limits
- **Total task count**: 205/273 (75%) - scope expanded by 46 tasks

**Completed**:

- ✅ **Day 15**: Voting & Synthesis - **🎉 MVP Complete!**
- ✅ **Day 14**: Information Gap Analysis & Research Integration
- ✅ **Day 12-13**: Multi-Round Deliberation (Facilitator orchestration, moderators, context building)
- ✅ **Day 11.5**: Prompt Broker Infrastructure (Unified LLM calls with metrics)
- ✅ **Day 10-11**: Persona Selection & Initial Round (Parallel expert contributions)
- ✅ **Day 8-9**: Problem Decomposition (Sub-problem generation)
- ✅ **Day 1-7**: Foundation (Models, LLM client, Redis, state management)

**Philosophy Changes**:

1. **AI-first validation**: Use Haiku ($0.001/check) instead of brittle pattern matching
2. **Expert-driven research**: Personas request research via XML tags, not pattern detection
3. **Embedding-based convergence**: Semantic similarity (Voyage AI) for quality metrics
4. **Upfront context gathering**: Resolve info gaps during decomposition, not mid-deliberation
5. **AI-driven vote synthesis**: Haiku intelligently aggregates votes, understands conditions/nuance ($0.002)
6. **Quality self-critique**: AI validates AI outputs (synthesis, persona selection, summaries) before presenting
7. **Research query validation**: Haiku validates/refines queries before expensive web search ($0.0005 saves $0.05)
8. **Adaptive summarization**: Information density determines summary length (75-150 tokens)
9. **Fully autonomous**: No user confirmation for persona selection - AI self-critiques and decides

---

## 💎 AI-First Quality & Cost Enhancements

**Goal**: Maximize quality while minimizing cost through intelligent AI validation layers

### Cost Impact Analysis

**Current Target**: $0.10/deliberation (35 persona calls + 6 summaries)

**AI-First Enhancements Added**:
- Vote aggregation (Haiku): +$0.002
- Synthesis quality validation (Haiku): +$0.003
- Research query validation (Haiku): -$0.025 (saves 0.5 bad queries × $0.05)
- Adaptive summarization (6 rounds): +$0.006
- Persona selection critique (Haiku): +$0.001
- Sub-problem validation (Haiku): +$0.001

**Net Impact**: **-$0.012** (SAVES money!)

**New Target**: **$0.088/deliberation** with significantly higher quality

### Quality Improvements

1. **Vote Synthesis**: Understands conditional votes, preserves minority views, captures nuance
2. **Research Efficiency**: Validates queries before $0.05 web search, refines vague queries
3. **Synthesis Quality**: Auto-validates completeness, revises if gaps found
4. **Adaptive Summaries**: High-info rounds get 150 tokens, low-info get 75 tokens
5. **Persona Selection**: Self-critique ensures diversity and domain coverage
6. **Sub-Problem Quality**: Pre-validates decomposition before user review

### ROI Examples

- Research validation: $0.0005 investment prevents $0.05 waste = **100x ROI**
- Vote synthesis: $0.002 replaces brittle logic, prevents synthesis errors
- Synthesis validation: $0.003 ensures final output quality (no user re-runs)

### Implementation Priority

**Day 15 (NEXT)**: Vote aggregation + synthesis validation
**Day 16-17**: Adaptive summarization
**Day 27**: Research query validation (highest ROI)

### Fallback Logging Standard (ALL Features)

**Requirement**: All fallback logic MUST include explicit logging with:
- ⚠️ emoji prefix for instant visibility
- Severity: ERROR (critical fallback) or WARNING (minor fallback)
- Clear explanation of what fallback is being used
- Impact statement (what functionality is degraded)
- Response/data preview for debugging (first 200 chars)

**Examples**:
```python
# Critical fallback (ERROR)
logger.error(
    f"⚠️ FALLBACK: AI vote synthesis FAILED. Using traditional aggregate_votes(). "
    f"Error: {e}. Impact: No conditional vote logic understanding."
)

# Minor fallback (WARNING)
logger.warning(
    f"⚠️ FALLBACK: Could not extract <tag>. Using full response. "
    f"Response: {content[:200]}..."
)
```

**Benefits**:
- Instantly visible in logs (⚠️ searchable)
- Clear impact assessment (user knows what's degraded)
- Debugging context (response preview, error message)
- Metrics tracking (model="fallback" for non-LLM paths)

**Apply to**: All JSON parsing, XML tag extraction, API calls, file operations, model selection, cache operations

---

## 🎯 Process Improvement: Early Critical Question Identification

**Priority**: MEDIUM - Improves UX by reducing interruptions

**Current State**:
- Information gaps are identified after problem decomposition
- User is prompted for critical internal answers during Step 2
- This creates a break in the flow after initial problem analysis

**Improvement**:
- Identify CRITICAL blocking questions during initial problem decomposition
- Prompt user for critical answers immediately (before decomposition completes)
- Only ask for NICE_TO_HAVE questions in Step 2 (Information Gap Detection)
- Benefits:
  - Reduces perceived wait time (user engaged throughout)
  - Better flow: Problem → Critical Q&A → Decomposition → Optional Q&A → Deliberation
  - Critical context available earlier for better decomposition

**Implementation Tasks** (Future):
- [ ] Update DecomposerAgent to identify critical questions during decomposition
- [ ] Add early Q&A prompt before decomposition result
- [ ] Filter out already-answered questions from Step 2
- [ ] Test flow with real problem scenarios
- [ ] Measure improvement in perceived UX

**Estimated Effort**: 1 day (Day 14.5 or integrate into Day 15)

---

## 🚀 v2 Enhancement: Intelligent Knowledge Caching System

**Priority**: HIGH VALUE - Dramatically reduces costs and improves quality over time

**Goal**: Build a shared knowledge pool that caches internal answers and external research, making the system smarter and cheaper with each use.

### Core Concept

Instead of re-asking the same questions or re-researching the same topics, create a persistent knowledge base that:
1. **Remembers user answers** to internal questions (with time-awareness)
2. **Caches external research** results (with expiration)
3. **Shares anonymized insights** across users (privacy-preserving)
4. **Uses embeddings** for semantic retrieval (not just exact matches)

### Architecture

#### 1. Internal Knowledge Cache (User-Specific)

**Data Model**:
```json
{
  "user_id": "user_123",
  "question": "What is your current churn rate?",
  "question_embedding": [0.123, 0.456, ...],  // Voyage AI embedding
  "answer": "5% monthly",
  "context": {
    "business_model": "B2B SaaS",
    "arr": "$100K",
    "customer_count": 50
  },
  "timeframe": "2025-11",  // When this answer applies
  "created_at": "2025-11-13T15:30:00Z",
  "expires_at": "2025-12-13T15:30:00Z",  // Auto-expire after 1 month
  "confidence": "high",  // User can mark if estimate vs exact
  "tags": ["metrics", "retention", "churn"]
}
```

**Features**:
- **Semantic matching**: Use embeddings to find similar questions (e.g., "monthly churn" vs "customer attrition rate")
- **Expiration logic**:
  - Metrics (churn, revenue, CAC): Expire monthly
  - Strategy (goals, priorities): Expire quarterly
  - Static facts (industry, business model): Never expire
- **Proactive prompts** (v2 web UI): "Your churn rate was 5% in November. Has this changed?"
- **Version history**: Track how answers change over time

**Storage**: PostgreSQL with pgvector extension for embedding search

#### 2. External Research Cache (Shared Pool)

**Data Model**:
```json
{
  "question": "What is average B2B SaaS churn rate?",
  "question_embedding": [0.789, 0.012, ...],
  "research_summary": "Industry benchmarks show average B2B SaaS monthly churn ranges from 3-7%, with SMB-focused products at 5-8% and enterprise at 1-2%. Annual churn typically 30-50% for SMB, 8-15% for enterprise.",
  "sources": [
    {"url": "https://example.com/saas-metrics", "title": "SaaS Metrics Guide", "date": "2024-10"},
    {"url": "https://example.com/churn-benchmarks", "title": "Churn Benchmarks", "date": "2025-01"}
  ],
  "research_date": "2025-11-13",
  "expires_at": "2026-02-13",  // Expire after 3 months (research goes stale)
  "search_queries_used": ["B2B SaaS churn rate", "SaaS retention benchmarks"],
  "confidence": "high",
  "usage_count": 42,  // How many users benefited from this research
  "cost_to_generate": 0.023,  // Track ROI (one research, many uses)
  "tags": ["saas", "metrics", "churn", "benchmarks"]
}
```

**Features**:
- **Semantic retrieval**: Find cached research for similar questions
- **Freshness tracking**:
  - Market research: 3 months
  - Technical benchmarks: 6 months
  - Regulatory info: 1 month
- **Cost savings metric**: Track $ saved by cache hits
- **Confidence scoring**: Degrade confidence as research ages
- **Source diversity**: Require 3+ sources for "high confidence"

**Storage**: PostgreSQL with pgvector + Redis for hot cache

#### 3. Anonymized Insights Pool (Multi-User Intelligence)

**Data Model**:
```json
{
  "question_category": "churn_rate",
  "filters": {
    "business_model": "B2B SaaS",
    "arr_range": "$50K-$250K",
    "customer_count_range": "10-100",
    "industry": "productivity_tools"
  },
  "aggregated_insights": {
    "median": "4.5%",
    "p25": "3.2%",
    "p75": "6.8%",
    "sample_size": 47,
    "last_updated": "2025-11-13"
  },
  "privacy_preserved": true,  // No individual data exposed
  "min_sample_size": 10  // Don't show if <10 users
}
```

**Features**:
- **Privacy-first**: Only show aggregates, require minimum sample sizes
- **Contextual filtering**: Match on business model, size, industry
- **Opt-in**: Users choose to contribute anonymized data
- **Value prop**: "Similar businesses to yours report 3-7% churn"
- **Confidence bands**: Show ranges, not just averages

**Use Cases**:
- "Businesses similar to yours (B2B SaaS, $50K-$250K ARR) report CAC of $500-$2000"
- "Solo founders in your situation typically allocate 15-25 hours/week to marketing"
- "Companies your size see 2-4% conversion rates on paid ads"

#### 4. Retrieval Strategy (Embedding-Based)

**Query Flow**:
1. **User asks a question** → Generate embedding (Voyage AI)
2. **Semantic search** → Query vector DB for similar questions (cosine similarity > 0.85)
3. **Check freshness** → Filter out expired entries
4. **Return cached answer** → If found, skip LLM call / web search
5. **Fallback** → If not found, generate new answer, cache it

**Cost Savings**:
- **Internal Q&A**: $0.00 (cache hit) vs $0.02 (LLM call)
- **External research**: $0.00 (cache hit) vs $0.05 (search + summarization)
- **ROI**: First research costs $0.05, next 100 uses are free → 100x ROI

#### 5. Implementation Phases

**Phase 1: Basic Caching (v2.0)**
- [ ] PostgreSQL schema for internal answers + external research
- [ ] pgvector extension for embedding search
- [ ] API endpoints: `/cache/internal/search`, `/cache/research/search`
- [ ] Expiration cron jobs (mark stale entries)
- [ ] Cache hit metrics (track savings)

**Phase 2: Proactive Updates (v2.1)**
- [ ] Web UI prompts: "Update your churn rate?"
- [ ] Email notifications: "Your CAC data is 2 months old"
- [ ] Trend analysis: "Your churn has increased 2% since last month"

**Phase 3: Shared Intelligence (v2.2)**
- [ ] Anonymized insights aggregation
- [ ] User opt-in system
- [ ] Privacy controls (what to share)
- [ ] Contextual matching (business model, size, industry)
- [ ] Insight display in deliberations: "Similar businesses report..."

**Phase 4: Advanced Features (v2.3+)**
- [ ] Auto-expiration with confidence decay
- [ ] Multi-language support (embeddings work cross-language)
- [ ] Research quality scoring (source credibility)
- [ ] User feedback loop ("Was this cached answer helpful?")
- [ ] Cost attribution (track $ saved per user)

### Technical Stack

**Database**:
- PostgreSQL 15+ with pgvector extension
- Tables: `user_internal_cache`, `external_research_cache`, `anonymized_insights`
- Indexes: GIN on embeddings, B-tree on timestamps/tags

**Embeddings**:
- Voyage AI `voyage-2` model (1536 dimensions)
- Cosine similarity threshold: 0.85 for matches
- Batch embedding for efficiency

**Cache Layer**:
- Redis for hot cache (frequently accessed research)
- TTL: 1 hour for hot entries
- Fallback to PostgreSQL for cold cache

**API Design**:
```python
# Search for cached internal answer
GET /api/v2/cache/internal/search
{
  "question": "What is your churn rate?",
  "user_id": "user_123",
  "context": {"business_model": "B2B SaaS"}
}
→ Returns: {found: true, answer: "5%", confidence: "high", age_days: 15}

# Search for cached research
GET /api/v2/cache/research/search
{
  "question": "What is average SaaS churn rate?",
  "max_age_days": 90
}
→ Returns: {found: true, summary: "...", sources: [...], age_days: 42}

# Get anonymized insights
GET /api/v2/insights/aggregate
{
  "category": "churn_rate",
  "filters": {"business_model": "B2B SaaS", "arr_range": "$50K-$250K"}
}
→ Returns: {median: "4.5%", p25: "3.2%", p75: "6.8%", sample_size: 47}
```

### Success Metrics

**Cost Reduction**:
- Target: 80% cache hit rate after 3 months
- Savings: ~$0.04 per cached internal answer
- Savings: ~$0.05 per cached research result
- ROI: 100x for shared research (one research, 100 users benefit)

**Quality Improvement**:
- Faster deliberations (skip Q&A for known answers)
- Richer context (anonymized benchmarks)
- Trend tracking (see how metrics change over time)

**User Experience**:
- Proactive updates ("Your data is stale")
- Peer benchmarking ("You're above/below average")
- Historical insights ("Your churn has improved 2% this quarter")

### Privacy & Ethics

**Principles**:
1. **User control**: Opt-in for sharing anonymized data
2. **Transparency**: Show what data is cached, when it expires
3. **Aggregation only**: Never expose individual user data
4. **Minimum sample sizes**: Require 10+ users before showing insights
5. **Right to deletion**: Users can purge their cached data

**Compliance**:
- GDPR-compliant (right to access, delete, export)
- No PII in anonymized pool
- Clear data retention policies

### Value Proposition

**For Users**:
- "Never answer the same question twice"
- "Get instant benchmarks from similar businesses"
- "Track how your metrics improve over time"

**For Platform**:
- Massive cost savings (80% reduction in redundant calls)
- Network effects (more users = richer insights)
- Competitive moat (knowledge base grows over time)

---

**Estimated Implementation**: 3-4 weeks for Phase 1, 2 weeks per subsequent phase

**Dependencies**: PostgreSQL, pgvector, Voyage AI, Redis (optional for hot cache)

**Priority**: Implement after v2.0 Web UI is stable (Week 5+)
