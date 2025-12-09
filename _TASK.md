## Audit-derived tasks (2025-12-08)

### P0 – Critical

- [x] [PERF][P0] Add composite index on `session_events(session_id, sequence)` for event ordering
- [x] [OBS][P0] Add correlation IDs – generate trace ID at API entry, pass through graph execution
- [x] [OBS][P0] Create `/health` endpoint with db/redis/llm connectivity checks (already exists: /api/health, /api/health/db, /api/health/redis, /api/health/anthropic)
- [x] [REL][P0] Add PostgreSQL connection retry with exponential backoff on pool exhaustion
- [x] [REL][P0] Add LLM rate limit handling – retry with backoff on 429 responses (already implemented in PromptBroker)

### P1 – High Value

- [x] [ARCH][P1] Add event handlers for `context_collection` and `analyze_dependencies` nodes (UI feedback gap)
- [x] [ARCH][P1] Emit `dependency_analysis_complete` event with execution_batches info
- [x] [PERF][P1] Batch contribution summarization – parallelize 3-5 summaries in event_collector
- [x] [PERF][P1] Refactor `list_by_user` to use JOINs instead of 4 correlated subqueries
- [x] [PERF][P1] Batch event persistence using `executemany` or `asyncio.gather`
- [x] [LLM][P1] Add input sanitization for `problem_statement` and `key_questions` before prompt interpolation
- [x] [LLM][P1] Validate output schema for facilitator decisions (ensure `action` field has valid value)
- [x] [LLM][P1] Enforce contribution length – truncate or retry contributions >300 words
- [x] [DATA][P1] Create Session Pydantic model – currently dict-based with no validation
- [x] [DATA][P1] Align ContributionMessage with DB schema – add `id`, `session_id`, `model`, `embedding` fields
- [x] [DATA][P1] Fix contribution_type/phase mismatch – use consistent enum values
- [x] [OBS][P1] Add cost anomaly alerts – flag sessions >$1.00
- [x] [OBS][P1] Log checkpoint operations – size, latency, errors
- [x] [OBS][P1] Capture SSE connection lifecycle – connect/disconnect events with client info
- [x] [API][P1] Document injection check in OpenAPI – security feature not visible in docs
- [x] [API][P1] Add SSE event versioning – include `event_version: 1` in payloads
- [x] [API][P1] Enforce problem_statement max length – add Pydantic Field(max_length=10000)
- [x] [API][P1] Add session*id regex validation – Pydantic validator for `bo1*[uuid]` format
- [x] [REL][P1] Implement circuit breaker for external APIs (Anthropic, Voyage, Brave)
- [x] [REL][P1] Add automatic session resume – reconnect SSE clients to in-progress sessions
- [x] [REL][P1] Add distributed locking for session status updates via Redis SETNX
- [x] [COST][P1] Enable prompt cache monitoring – track cache hit rate in metrics dashboard
- [x] [COST][P1] Add contribution length validation – reject contributions >300 tokens, request retry

### P2 – Nice to Have

- [ ] [ARCH][P2] Remove or make configurable the 2s event verification delay
- [ ] [PERF][P2] In-memory persona profile cache during meeting execution
- [ ] [PERF][P2] Pre-compute session summary counts on write (denormalization)
- [ ] [LLM][P2] Add jailbreak detection – pattern match for "ignore previous instructions" in problem statements
- [ ] [LLM][P2] Token budget tracking per prompt – log input token counts to identify bloated prompts
- [ ] [DATA][P2] Squash migrations – create consolidated baseline for new deployments
- [ ] [DATA][P2] Add model validation tests – ensure roundtrip serialization works
- [ ] [OBS][P2] Add structured JSON logging – replace text logs with structured format
- [ ] [OBS][P2] Create observability dashboard – Grafana/DataDog metrics
- [ ] [OBS][P2] Add client error reporting – frontend → backend error bridge
- [ ] [API][P2] Add OpenAPI spec versioning – `/api/v1/` prefix already used, formalize
- [ ] [API][P2] Create SDK types package – TypeScript types for frontend consumption
- [ ] [REL][P2] Add LLM fallback provider – OpenAI as backup for Anthropic outages
- [ ] [REL][P2] Extend checkpoint TTL or add PostgreSQL-based checkpointing
- [ ] [REL][P2] Add chaos testing – validate recovery paths with fault injection
- [ ] [COST][P2] Cache quality check aspect coverage – store per-round, invalidate on new contributions
- [ ] [COST][P2] Batch embedding API calls – group 5 contributions per Voyage call
- [ ] [COST][P2] Use Haiku for routine facilitator decisions – route "continue round" to Haiku
- [ ] [COST][P2] Add cost budget alerts – warn at 80% of $0.50 threshold
- [ ] [COST][P2] Implement adaptive expert count – 3 for simple, 5 for complex problems
