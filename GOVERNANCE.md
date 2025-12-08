# GOVERNANCE.md
GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.
DO NOT LOAD BY DEFAULT. Load single tagged section on demand.

<code_quality>
Run `make pre-commit` before push.
- Python: ruff + mypy
- Frontend: eslint + prettier + svelte-check
- No dead code, no bare except
</code_quality>

<architecture>
LangGraph state machine, 5-layer loop prevention.
- Graph: decompose → personas → rounds → convergence → synthesis
- Limits: 20 recursion, 6 rounds
- Parallel: asyncio.gather when ENABLE_PARALLEL_ROUNDS=true
- State: Redis checkpoint; Events: SSE
- MUST NOT alter meeting progression logic without explicit request
</architecture>

<security>
SuperTokens auth, no hardcoded secrets.
- Production: ENABLE_SUPERTOKENS_AUTH=true
- Secrets in .env only, never commit
- Validate user input at API boundaries
- SQL: parameterized queries only
</security>

<agent_governance>
Personas debate, facilitator orchestrates.
- 3-5 experts adaptive; recommendations not votes
- Phases: Exploration → Challenge → Convergence
- Cost target: ~$0.10/deliberation
SAFETY CONSTRAINTS:
- Persona roles MUST NOT be modified unless explicitly requested
- Meeting progression (Exploration→Challenge→Convergence) MUST NOT be altered
- Scoring criteria MUST remain consistent across runs
- Decision summaries MUST remain structurally stable
- MUST NOT introduce circular reasoning loops between agents
- MUST NOT allow personas to override global meeting constraints
- MUST NOT expand number of steps without request
- Agent-to-agent reasoning MUST remain shallow unless correctness risk high
</agent_governance>

<llm_rules>
Prompt caching, model via config.
- Models: sonnet (default), haiku (summarize), opus (complex)
- AI_OVERRIDE=true for testing
- XML tags for structured output
</llm_rules>

<testing>
Pytest with fixtures.
- `make test`; tests/ mirrors bo1/
- Mock LLM; integration in tests/integration/
</testing>

<deployment>
Blue-green, auto migrations.
- GitHub Actions deploy; migrations before cutover
- nginx serves static, not Node
</deployment>

<performance>
Pooling, parallel, caching.
- db_session() pool; asyncio.gather
- Semantic dedup 0.80; prompt cache 90%
</performance>

<reference>
DO NOT LOAD. Pointers only.
- Flags: .env
- Migrations: migrations/versions/
- Personas: bo1/data/personas.json (45)
</reference>

<audit_pattern>
Manifest-driven audits. Load manifest, not inline.
- Manifests: audits/manifests/{audit_type}.manifest.xml
- Reports: audits/reports/{audit_type}.report.md
- Loader: audits/loader.claude
RULES:
- Every audit prompt MUST begin with <load_manifest path="...">
- Every audit MUST reference manifest for scope/constraints/outputs
- MUST NOT copy manifest contents into prompts
- MUST follow expected_outputs format exactly
- MUST respect activation_conditions
Available audits: architecture_flow, performance_scalability, llm_alignment, data_model, observability, api_contract, reliability, cost_optimisation
</audit_pattern>

<governance_checkpoint>
Claude MUST:
1. Check no governance is being modified without explicit request
2. STOP if edit would alter governance intent
3. Ask explicit confirmation before modifying any governance file
4. Reject changes that weaken constraints or remove rules unless user-initiated
5. Validate operation aligns with context_boundary, model_guidance, task_patterns
If ANY fails → STOP and ask user
</governance_checkpoint>

<agent_integrity_gate>
Claude MUST verify:
1. Persona roles unchanged
2. Meeting-state transitions unchanged
3. Judge scoring/evaluation rules unchanged
4. No new agent roles created without instruction
5. No agent cross-talk or loop behaviour introduced
6. Agent summaries/action formats stable
If ANY fails → STOP and ask user
</agent_integrity_gate>

<policy_violation_detector>
POLICY VIOLATIONS (must abort + inform user):
1. Modifying persona/agent/meeting logic without explicit instruction
2. Weakening or deleting governance constraints
3. Expanding context beyond CONTEXT_BOUNDARY limits
4. Escalating model/reasoning without MODEL_GUIDANCE conditions
5. Rewriting large files when small diff suffices
6. Loading irrelevant folders or governance sections
On violation → abort, report which rule violated, request confirmation
</policy_violation_detector>
