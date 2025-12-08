<load_manifest path="audits/manifests/cost_optimisation.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>cost_optimisation</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Reduce LLM, infra, and storage cost while preserving output quality.
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
    <cost_audit>
      <cost_drivers>Bullets of main drivers.</cost_drivers>
      <issues>5–10 high-cost behaviours.</issues>
      <recommendations>
        <prompt_optimisations>3–7 safe prompt reductions.</prompt_optimisations>
        <model_tiering>Where to downshift models.</model_tiering>
        <caching>High-value cache points.</caching>
        <infra>2–5 infra-level cost adjustments.</infra>
      </recommendations>
      <next_steps>Top 5 cost-saving actions.</next_steps>
    </cost_audit>
  </output_format>
</audit_request>
