<framework_request>
  <type>manifest_generator</type>
  <name>Generate Audit Manifests</name>

  <goal>
    Generate audit manifest files for the project in audits/manifests/.
    Each manifest defines what the audit is, when it runs, inputs, outputs, and execution pattern.
  </goal>

  <constraints>
    - Follow CLAUDE.md, GOVERNANCE.md, CONTEXT_BOUNDARY, MODEL_GUIDANCE, TASK_PATTERNS.
    - Keep each manifest short, shallow, token-efficient.
    - Do not load or reproduce unnecessary code.
    - Never output chain-of-thought or long reasoning.
  </constraints>

  <audit_types>
    1. architecture_flow
    2. performance_scalability
    3. llm_alignment
    4. data_model
    5. observability
    6. api_contract
    7. reliability
    8. cost_optimisation
  </audit_types>

  <file_naming>
    audits/manifests/{audit_type}.manifest.xml
  </file_naming>

  <canonical_structure>
    <audit_manifest>
      <audit_type>...</audit_type>
      <purpose>1-2 sentences</purpose>
      <scope>Bullet list of what audit examines</scope>
      <constraints>Governance rules, boundaries, limitations</constraints>
      <required_inputs>Data, files, system knowledge needed</required_inputs>
      <expected_outputs>Structural outputs matching output_format</expected_outputs>
      <activation_conditions>When audit should run</activation_conditions>
      <run_pattern>Instructions for execution</run_pattern>
    </audit_manifest>
  </canonical_structure>

  <output_format>
    - Summary of files created/updated
    - Short verification checklist
  </output_format>
</framework_request>
