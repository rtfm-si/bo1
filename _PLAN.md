# Plan: Prompts Conciseness Enhancement (Task #6)

## Summary

- Add conciseness directive to COMMUNICATION_PROTOCOL (shared across all persona prompts)
- Reduce contribution length guidance from 150-250 words to 100-150 words
- Add explicit anti-verbosity examples to BEHAVIORAL_GUIDELINES
- Update synthesis templates to request shorter, punchier outputs

## Implementation Steps

1. **Update COMMUNICATION_PROTOCOL** in `bo1/prompts/protocols.py`
   - Change contribution guidance: "100-150 words" (was 150-250)
   - Add: "Brevity over completeness. One insight > many points."
   - Add: "Cut filler phrases: 'I think', 'It's worth noting', 'In my opinion'"

2. **Add anti-verbosity examples** to BEHAVIORAL_GUIDELINES in `bo1/prompts/protocols.py`
   - New NEVER item: "Write long contributions when a short one suffices"
   - Add bad/good example pair showing verbose vs concise contribution

3. **Update persona.py user_message** in `compose_persona_contribution_prompt()`
   - Change "(Public statement to the group - 2-4 paragraphs)" to "(Public statement - 1-2 paragraphs max)"

4. **Update synthesis word budget** in `bo1/prompts/synthesis.py`
   - SYNTHESIS_LEAN_TEMPLATE: "~600-800 words" → "~400-600 words"
   - Add: "Every sentence must earn its place"

## Tests

- Unit tests:
  - None needed - prompt text changes only, no logic changes

- Manual validation:
  - Run a meeting and observe contribution lengths
  - Compare synthesis output word count before/after
  - Verify contributions remain substantive despite being shorter

## Dependencies & Risks

- Dependencies: None

- Risks:
  - Contributions may become too terse and lose nuance → mitigate by keeping "substantive" requirement
  - Synthesis may omit important details → mitigate by keeping structure, just tightening prose
