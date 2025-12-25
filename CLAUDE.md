# CLAUDE.md

GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.

<system_context>
Bo1: Multi-agent deliberation. Personas debate decisions.
Stack: LangGraph + FastAPI + SvelteKit + Postgres + Redis
ssh for prod: ssh root@139.59.201.65
</system_context>

<critical_rules>

- CONCISE: brevity over grammar
- DIFFS ONLY: never full files; micro-diffs preferred
- MINIMAL CONTEXT: load smallest relevant tag only
- Local CLAUDE.md overrides root; root overrides GOVERNANCE.md
- Manifests define folder scope—respect boundaries
- Terminology: UI=meeting/decision/expert; API=session/problem_statement/persona
- recommendations NOT votes: collect_recommendations()
- db_session() always; Docker hostnames not localhost
- Frontend: $env/dynamic/public not import.meta.env
  </critical_rules>

<efficiency_rules>

- Load one governance tag at a time, never sibling tags
- Skip <reference> always unless explicitly requested
- Max 3 bullets; prefer code over prose
- Never restate user context
- Shallow reasoning default (≤4 steps); deepen only for correctness risk
- Ask clarification only when failure likely
- Never assume missing context; ask first
  </efficiency_rules>

<governance_constraints>

- MUST NOT self-modify governance without explicit user request
- MUST NOT silently change constraints or defaults
- MUST NOT expand reasoning beyond defined limits
- MUST NOT add new tags or sections without user instruction
- MUST NOT reinterpret ambiguous rules; ask user
- MUST NOT infer new implied rules
- MUST NOT invent new workflow steps
- MUST NOT load untagged sections
- Conflict resolution: local CLAUDE.md → root CLAUDE.md → GOVERNANCE.md
  </governance_constraints>

<workflows>
```bash
make up / shell / test / pre-commit
uv run alembic upgrade head
```
Flow: Problem → Decompose → Personas (3-5) → Rounds → Synthesis
Patterns: serialize_state_for_checkpoint() / deserialize_state_from_checkpoint(); db_session(); SSE via event_collector
</workflows>

<file_map>
Core: bo1/graph/{config,state,nodes/}, bo1/prompts/, bo1/models/
Backend: backend/api/{main,event_collector,middleware/auth}.py
Frontend: frontend/src/{routes/,lib/components/}
</file_map>

<governance_reference>
DO NOT LOAD BY DEFAULT. Load single tag on demand:

- GOVERNANCE.md - <code_quality|architecture|security|agent_governance|llm_rules|testing|deployment|performance|audit_pattern>
- CONTEXT_BOUNDARY.md - scope limits
- MODEL_GUIDANCE.md - reasoning depth
- TASK_PATTERNS.md - <bugfix|feature|refactor|review|migration>\_pattern
- TAGS.md - tag semantics
- DOMAIN_KNOWLEDGE.md - only if task requires domain context
  </governance_reference>

<audit_rules>
All audits MUST:

- Load manifest via <load_manifest path="audits/manifests/{audit_type}.manifest.xml" />
- NOT operate without corresponding manifest
- Follow manifest constraints and expected_outputs exactly
- Output reports to audits/reports/{audit_type}.report.md
  Audits MUST NOT inline or copy manifest contents into prompts.
  </audit_rules>

<pre_flight_enforcement>
Claude MUST run BEFORE any request:

1. Identify working folder
2. Load ONLY nearest folder CLAUDE.md + manifest.md
3. Load ONLY minimal required tags from governance files
4. Resolve conflicts: folder CLAUDE → root CLAUDE → GOVERNANCE → TAGS.md
5. Validate scope: no unrelated folders, no full directory scans, respect context limits
6. Validate tokens: reasoning ≤4 steps, diffs only, no full files
7. Validate safety: no persona/agent/meeting changes without explicit request
8. If ANY fails → STOP and ask user
   </pre_flight_enforcement>

<runtime_self_audit>
Claude MUST run BEFORE sending any final answer:

1. Re-check loaded context obeyed CONTEXT_BOUNDARY, MODEL_GUIDANCE, folder scope
2. Re-check proposed change: no governance/agent/meeting alterations unless requested; minimal diffs
3. Re-check output: no unnecessary prose, no large unchanged blocks, no secrets
4. If violation found → abort draft, correct, then send revised
5. If correction impossible without breaking rules → STOP and ask user
   </runtime_self_audit>

<hallucination_guard>
Claude MUST:

1. Prefer concrete repo evidence over assumptions
2. Never invent file paths, APIs, or entities that do not exist
3. If unsure whether function/file exists, check repo or ask user
4. If change conflicts with existing code, highlight conflict and ask
   </hallucination_guard>
