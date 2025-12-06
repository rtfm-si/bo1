Meeting System Deep Dive Test

Objective

Start a new meeting via API calls (no UI), follow it through logs and database queries, actively participate when needed, and analyze every aspect of
the system's performance.

Test Execution

1. Setup Monitoring

- Tail API container logs with timestamps
- Set up database query monitoring
- Prepare to capture all SSE events

2. Create Meeting via API

Start a meeting with a moderately complex decision that will exercise the full graph:

Suggested test problem: "Should our startup pivot from B2B to B2C, or pursue a hybrid model? We have 18 months runway, 500 B2B customers, and see 10x
larger B2C market opportunity but would need to rebuild our sales motion."

3. Active Monitoring & Participation

- Follow SSE event stream for the session
- Watch for context_insufficient events - provide clarifying context if triggered
- Monitor round progression, expert contributions, convergence signals

4. Analysis Checklist

Graph Flow Analysis:

- Verify correct node sequence execution
- Check for unexpected loops or repeated nodes
- Confirm round limits respected
- Validate convergence detection timing

Timing & Performance:

- Measure time per LLM call
- Identify dead time between operations
- Find redundant/duplicate calls
- Calculate total deliberation time
- Check for serialization where parallelization is possible

Prompt Quality Scoring (1-10 scale):

- Decomposition prompt → quality of sub-problems generated
- Persona selection prompt → relevance of experts chosen
- Contribution prompts → depth and usefulness of responses
- Facilitator decision prompts → appropriateness of flow decisions
- Synthesis prompts → coherence and actionability of final output

Response Quality Scoring (1-10 scale):

- Expert contributions: Are they substantive or generic?
- Do experts build on each other or repeat points?
- Is semantic deduplication working (0.80 threshold)?
- Final synthesis: Actionable? Addresses original problem?

Error Detection:

- Any unhandled exceptions in logs
- JSON parsing failures
- Database connection issues
- Rate limiting triggers
- Timeout or loop prevention activations

5. Parallelization Opportunities

Identify any sequential operations that could run concurrently:

- Expert contributions within a round (should already be parallel)
- Sub-problem deliberations (flag-controlled)
- Database writes vs LLM calls

6. Deliverables

After meeting completes, provide:

1. Timeline diagram of all operations with durations
2. Prompt scorecard with specific improvement suggestions
3. Response quality report with examples
4. Performance bottleneck list ordered by impact
5. Bug/error list if any found
6. Parallelization recommendations with expected time savings

Write the analysis to a file in root

---

Execute this test, participate as needed, and deliver a comprehensive analysis.
