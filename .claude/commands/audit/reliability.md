<load_manifest path="audits/manifests/reliability.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>reliability</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Identify failure modes and propose resilience improvements.
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
    <reliability_audit>
      <failure_modes>5–10 key failure modes.</failure_modes>
      <current_behaviour>How system currently responds.</current_behaviour>
      <recommendations>Retries, idempotency, checkpointing, error UX.</recommendations>
      <next_steps>Top 5 reliability upgrades.</next_steps>
    </reliability_audit>
  </output_format>
</audit_request>
