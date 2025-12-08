<load_manifest path="audits/manifests/observability.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>observability</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Evaluate logs, metrics, and tracing for diagnosability.
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
    <observability_audit>
      <current_state>Summary of log/metric landscape.</current_state>
      <gaps>5–10 observability gaps.</gaps>
      <recommendations>
        <logging>Minimal structured logging format.</logging>
        <metrics>5–10 high-value metrics.</metrics>
        <dashboards>3–5 dashboard ideas.</dashboards>
      </recommendations>
      <next_steps>5–10 sprint tasks.</next_steps>
    </observability_audit>
  </output_format>
</audit_request>
