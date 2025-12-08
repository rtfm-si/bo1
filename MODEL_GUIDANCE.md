# MODEL_GUIDANCE.md
GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.

<model_selection>
Default: smallest competent model.
- Simple ops: no special model
- Architecture/security: deeper reasoning
- Bo1 internal: Sonnet (default), Haiku (summarize), AI_OVERRIDE for testing
- MUST NOT escalate model unless: (a) correctness impossible otherwise, (b) user explicitly requests
</model_selection>

<reasoning_depth>
Shallow (default, ≤4 steps): syntax, search, CRUD
Medium: multi-file refactor, features, tests
Deep: security, architecture, migrations
- MUST NOT expand beyond ≤4 steps without explicit correctness justification
- Verbose reasoning MUST be suppressed unless user opts into deep mode
</reasoning_depth>

<output_rules>
- 1-3 bullets + diff
- Never explain unless asked
- Changed lines only; micro-diffs preferred
- MUST NOT rewrite entire files unless user explicitly requests full rewrite
- MUST NOT include unchanged code in diffs
</output_rules>

<fallbacks>
- Unsure scope: ask first
- Unclear task: 1-2 questions max
- Stuck: state blocker, suggest alternatives
- Ambiguous rule: MUST pause and ask user
</fallbacks>

<enforcement_guard>
Before ANY operation:
1. Confirm smallest viable model
2. Enforce reasoning-depth cap (≤4 steps default)
3. Verify output constraints (diff-only, minimal text)
4. Refuse tasks requiring implicit full-file scans
5. Ask confirmation before escalating model size
If ANY fails → STOP and ask user
</enforcement_guard>
