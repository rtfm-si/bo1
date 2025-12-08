<load_manifest path="audits/manifests/llm_alignment.manifest.xml" />

<manifest_reference>
  Use the loaded audit manifest to:
  - enforce scope
  - enforce constraints
  - ensure required_inputs are gathered
  - produce exactly the expected_outputs
  - respect activation_conditions
</manifest_reference>

<audit_request>
  <audit_type>llm_alignment</audit_type>

  <goal>
    Follow the purpose and scope defined in the manifest.
    Evaluate prompt clarity, persona alignment, hallucination risk, and multi-agent coordination.
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
    <llm_alignment_audit>
      <prompt_inventory>List key templates + roles.</prompt_inventory>
      <issues>5–10 prompt/behavioural issues.</issues>
      <prompt_improvements>Concrete edits with short before/after snippets.</prompt_improvements>
      <agent_dynamics>Strengths/weaknesses of personas/moderators/judge.</agent_dynamics>
      <cost_alignment>Where to shorten prompts or downgrade models.</cost_alignment>
    </llm_alignment_audit>
  </output_format>
</audit_request>
