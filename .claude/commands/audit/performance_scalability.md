<load_manifest path="audits/manifests/performance_scalability.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>performance_scalability</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Identify bottlenecks, reduce latency, improve throughput.
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
    <performance_audit>
      <critical_paths>Latency breakdown for core flows.</critical_paths>
      <bottlenecks>5–10 performance issues.</bottlenecks>
      <recommendations>
        <parallelisation>3–5 opportunities.</parallelisation>
        <caching>3–5 places to cache prompts/results.</caching>
        <db>3–5 DB tuning suggestions.</db>
        <models>Where to downshift from Sonnet to Haiku.</models>
      </recommendations>
      <next_steps>5–10 sprint tasks.</next_steps>
    </performance_audit>
  </output_format>
</audit_request>
