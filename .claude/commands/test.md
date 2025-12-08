<load_manifest path="audits/manifests/test.manifest.xml" />

<manifest_reference>
Use the loaded audit manifest to:

- enforce scope
- enforce constraints
- ensure required_inputs are gathered
- produce exactly the expected_outputs
- respect activation_conditions
  </manifest_reference>

<audit_request>
<audit_type>test</audit_type>
<name>Meeting System Deep Dive Test (No UI)</name>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Run a full meeting via API only, monitor behaviour, analyze and report.
  </goal>

<test_scenario>
"Should our startup pivot from B2B to B2C, or pursue a hybrid model? We have 18 months runway, 500 B2B customers, and see 10x larger B2C market opportunity but would need to rebuild our sales motion."
</test_scenario>

  <constraints>
    - Follow manifest constraints.
    - Follow CLAUDE.md, GOVERNANCE.md, CONTEXT_BOUNDARY, MODEL_GUIDANCE, TASK_PATTERNS.
    - Keep reasoning shallow and outputs compact.
    - Focus on evidence and actionable changes.
    - No unnecessary file dumps.
  </constraints>

  <steps>
    Derive all steps from the manifest's <scope>, <required_inputs>, and <expected_outputs>.
  </steps>

<output_format> 1. Timeline overview: bullet sequence with durations, note bottlenecks. 2. Prompt scorecard: each prompt type 1-10 + improvement bullets. 3. Response quality: scores + concrete examples (good + bad). 4. Performance bottlenecks: ordered by impact with suggested fixes. 5. Bugs/errors: list with locations and root causes. 6. Parallelisation opportunities: where to add concurrency.
Write report to /meeting_system_deep_dive.md
</output_format>
</audit_request>
