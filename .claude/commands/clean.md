<load_manifest path="audits/manifests/clean.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>clean</audit_type>
  <name>Codebase Cleanup Audit</name>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Audit and clean the codebase: remove legacy code, consolidate duplicates, clean DB schema.
  </goal>

  <constraints>
    - Follow manifest constraints.
    - Follow CLAUDE.md, GOVERNANCE.md, CONTEXT_BOUNDARY, MODEL_GUIDANCE, TASK_PATTERNS.
    - Breaking changes allowed (no live customers).
    - End result MUST work (build, tests, migrations pass).
    - Keep reasoning shallow and outputs compact.
    - No unnecessary file dumps.
  </constraints>

  <steps>
    Derive all steps from the manifest's <scope>, <required_inputs>, and <expected_outputs>.
  </steps>

  <output_format>
    Step 1: Short bullet list of domains and suspected legacy/unused areas.
    Step 2: Concise list of top consolidation targets per domain.
    Step 3: Files marked DELETE NOW / REVIEW BEFORE DELETE.
    Step 4: Short migration plan (columns/tables to drop, code to update).
    Step 5-6: Iterative refactor with minimal diffs.
    Step 7: Final summary written to /_PLAN.md
  </output_format>
</audit_request>
