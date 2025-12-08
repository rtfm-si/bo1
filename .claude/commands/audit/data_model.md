<load_manifest path="audits/manifests/data_model.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>data_model</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Audit schema, migrations, relationships, unused columns/tables, and data lifecycle.
  </goal>

  <constraints>
    - Follow manifest constraints.
    - Follow CLAUDE.md, GOVERNANCE.md, CONTEXT_BOUNDARY, MODEL_GUIDANCE, TASK_PATTERNS.
    - Keep reasoning shallow and outputs compact.
    - No unnecessary file dumps.
  </constraints>

  <steps>
    Derive all steps from the manifest's <scope>, <required_inputs>, and <expected_outputs>.
  </steps>

  <output_format>
    <data_model_audit>
      <entity_map>Main tables with purpose bullets.</entity_map>
      <issues>5–10 schema issues.</issues>
      <cleanup_plan>Columns/tables to remove or merge.</cleanup_plan>
      <migration_outline>Steps for 2–3 high-value migrations.</migration_outline>
      <next_steps>Top 5 cleanup tasks.</next_steps>
    </data_model_audit>
  </output_format>
</audit_request>
