# TAGS.md
GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.
Canonical tag definitions. Do not duplicate elsewhere.

<tag_definitions>
CLAUDE.md (always loaded, kept small):
- <system_context> project overview
- <critical_rules> must-follow
- <efficiency_rules> token optimization
- <governance_constraints> immutability rules
- <workflows> commands/flows
- <file_map> key locations
- <governance_reference> pointers
- <pre_flight_enforcement> mandatory pre-task checks
- <runtime_self_audit> pre-answer verification
- <hallucination_guard> evidence-based constraints

GOVERNANCE.md (load single tag on demand):
- <code_quality> <architecture> <security> <agent_governance>
- <llm_rules> <testing> <deployment> <performance>
- <reference> NEVER AUTO-LOAD
- <governance_checkpoint> modification gates
- <agent_integrity_gate> agent safety checks
- <policy_violation_detector> violation detection + abort

TASK_PATTERNS.md (load single pattern):
- <bugfix_pattern> <feature_pattern> <refactor_pattern>
- <review_pattern> <migration_pattern>
- <post_task_checks> mandatory post-pattern verification

DOMAIN_KNOWLEDGE.md (load only if domain-relevant):
- <meetings> <personas> <constraints> <cost_model> <user_flows>

MODEL_GUIDANCE.md:
- <model_selection> <reasoning_depth> <output_rules> <fallbacks>
- <enforcement_guard> pre-operation checks

TAGS.md:
- <tag_definitions> <loading_rules> <tag_constraints>
- <enforcement_rules> tag validation

Folder files:
- <local_enforcement> folder-specific pre-checks
- <local_self_audit> folder-specific pre-reply checks
</tag_definitions>

<loading_rules>
Auto-load: CLAUDE.md only
On-demand single tag: GOVERNANCE.md, TASK_PATTERNS.md
Domain-relevant only: DOMAIN_KNOWLEDGE.md
Never auto-load: <reference>, folder manifests, zzz_*
MUST NOT load sibling tags unless task spans multiple concerns
MUST NOT load untagged sections
Unrecognised tags MUST be ignored
</loading_rules>

<tag_constraints>
- Each tag has single meaning; never overloaded
- New tags MUST NOT be created without explicit user instruction
- Tags MUST NOT be redefined in other files
- Claude MAY load only the specific tagged subsection required
</tag_constraints>

<enforcement_rules>
Claude MUST:
1. Validate referenced tag exists in TAGS.md
2. Refuse to load unknown/undefined tags
3. Never create new tags without explicit user instruction
4. Never reinterpret tag meaning outside TAGS.md
5. Load ONLY the tag requested or required for correctness
If validation fails → STOP and ask user
</enforcement_rules>
