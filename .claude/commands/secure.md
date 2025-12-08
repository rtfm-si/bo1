<load_manifest path="audits/manifests/secure.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>secure</audit_type>
  <name>Full-Spectrum Security Audit (Red Team + Blue Team)</name>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Identify vulnerabilities, misconfigurations, weak patterns, unsafe flows.
    Propose concise, actionable fixes.
  </goal>

  <constraints>
    - Follow manifest constraints.
    - Follow CLAUDE.md, GOVERNANCE.md, CONTEXT_BOUNDARY, MODEL_GUIDANCE, TASK_PATTERNS.
    - Breaking changes allowed.
    - Keep outputs concise (bullets).
    - Use minimal diffs, shallow reasoning.
    - No full-file dumps unless essential.
  </constraints>

  <steps>
    Derive all steps from the manifest's <scope>, <required_inputs>, and <expected_outputs>.
  </steps>

  <output_format>
    Step 1: Short map of attackable surfaces, trust boundaries, data flow paths.
    Step 2: Vulnerability list (category, vector, impact, likelihood).
    Step 3: Fix Pack (high→medium→low priority, 1-2 line remediation each).
    Step 4: Security test plan checklist.
    Step 5: Minimal diff patches for highest-priority issues.
    Step 6: Final report written to /security_audit_report.md
  </output_format>
</audit_request>
