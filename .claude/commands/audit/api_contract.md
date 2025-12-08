<load_manifest path="audits/manifests/api_contract.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>api_contract</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Review API surface for consistency, clarity, safety, and correctness.
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
    <api_audit>
      <endpoint_map>List endpoints + auth requirements.</endpoint_map>
      <issues>5–10 API issues.</issues>
      <recommendations>Endpoint changes and error schema standard.</recommendations>
      <next_steps>Top 5 contract improvements.</next_steps>
    </api_audit>
  </output_format>
</audit_request>
