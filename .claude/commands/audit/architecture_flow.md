<load_manifest path="audits/manifests/architecture_flow.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>architecture_flow</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Map system architecture, identify structural issues, propose simplified vNext design.
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
    <architecture_audit>
      <current_map>Bullet overview of major components and flows.</current_map>
      <issues>5–10 architecture issues.</issues>
      <target_architecture>1–2 diagrams (text arrows) + bullets.</target_architecture>
      <high_impact_changes>3–7 refactor suggestions.</high_impact_changes>
      <next_steps>5–10 actions for a cleanup sprint.</next_steps>
    </architecture_audit>
  </output_format>
</audit_request>
