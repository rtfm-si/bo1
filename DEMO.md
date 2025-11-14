# Board of One - Demo Guide

This document describes the available demos for validating the complete Board of One pipeline.

---

## Available Demos

### 1. Standard Demo (Weeks 1-2)
**Command**: `make demo` or `make demo-interactive`

Demonstrates the core pipeline (Days 1-15):
- Problem decomposition
- Information gap detection
- Context collection
- Persona selection
- Multi-round deliberation
- Voting and synthesis

**Duration**: ~3-5 minutes
**Cost**: ~$0.15-0.25

### 2. Full Pipeline Demo (Weeks 1-3) ✨ NEW
**Command**: `make demo-full` or `make demo-full-interactive`

Demonstrates the COMPLETE pipeline with all Week 3 optimizations:
- Everything from standard demo, PLUS:
- **Hierarchical context management** (prevents quadratic token growth)
- **Background async summarization** (non-blocking)
- **Prompt caching** (80%+ cache hit rate, 90% cost reduction)
- **Optimal model allocation** (Sonnet for personas, Haiku for summaries)
- **Real-time metrics tracking** (cost, tokens, cache performance)

**Duration**: ~5-8 minutes
**Cost**: ~$0.10-0.15 (70% cheaper than naive implementation)

---

## Running the Demos

### Automated Mode (Default)
No user input required - uses pre-configured problem scenario:

```bash
make demo-full
```

**Use cases**:
- CI/CD validation
- Cost/performance benchmarking
- Quick system health check
- Automated testing

### Interactive Mode
Prompts for user input at key decision points:

```bash
make demo-full-interactive
```

**Use cases**:
- Demonstrating to stakeholders
- Testing custom scenarios
- User training
- Feature exploration

---

## What Gets Validated

### Core Functionality
- ✅ Problem decomposition (atomic vs complex)
- ✅ Persona selection (domain-matched experts)
- ✅ Parallel LLM calls (initial round)
- ✅ Sequential multi-round deliberation
- ✅ Facilitator orchestration
- ✅ Voting mechanism
- ✅ Synthesis generation & validation

### Week 3 Optimizations
- ✅ **Hierarchical Context**: Old rounds summarized, current round full detail
- ✅ **Async Summarization**: Background task doesn't block next round
- ✅ **Prompt Caching**: 80%+ cache hit rate on Sonnet 4.5
- ✅ **Model Optimization**: Right model for each role (Sonnet vs Haiku)
- ✅ **Cost Tracking**: Real-time metrics, token usage, cache performance

---

## Expected Output

### Demo Sections

1. **STEP 1: Problem Decomposition**
   - Analyzes complexity
   - Breaks into sub-problems (if complex)
   - Identifies dependencies

2. **STEP 2: Persona Selection**
   - Selects 3-5 domain experts
   - Shows persona names and specializations

3. **STEP 3: Initialize Deliberation**
   - Creates deliberation state
   - Shows adaptive round limits

4. **STEP 4: Initial Round**
   - All personas contribute in parallel
   - Shows cache metrics (if available)

5. **STEP 5: Multi-Round Deliberation**
   - Facilitator decides continue/vote/research
   - Shows hierarchical context in action
   - Displays background summarization status
   - Tracks context growth (linear, not quadratic)

6. **STEP 6: Voting**
   - All personas cast votes
   - Shows prompt caching performance (80%+ hit rate)
   - AI aggregates votes

7. **STEP 7: Synthesis**
   - Generates final recommendation
   - Validates quality
   - Revises if needed

8. **STEP 8: Week 3 Validation**
   - Table showing all Week 3 features
   - Confirmation each optimization is active

### Final Metrics Table

```
┌────────────────────────────┬──────────────────┬────────────────────────┐
│ Metric                      │ Value            │ Notes                  │
├────────────────────────────┼──────────────────┼────────────────────────┤
│ Total LLM Calls            │ 15-25            │ All API requests       │
│ Total Tokens               │ 20,000-40,000    │ In + Out               │
│ Cache Performance          │ 70-85% hit rate  │ Week 3 optimization    │
│ Total Cost                 │ $0.10-0.15       │ Target: <$0.50         │
│ Total Duration             │ 120-180s         │ End-to-end             │
│ Deliberation Rounds        │ 2-4              │ Adaptive (max 10)      │
│ Personas Consulted         │ 5                │ Expert panel size      │
│ Contributions              │ 10-25            │ Total expert inputs    │
└────────────────────────────┴──────────────────┴────────────────────────┘
```

---

## Success Criteria

The demo validates the system is working correctly if:

### ✅ Core Pipeline
- [ ] Problem decomposes appropriately (atomic or split)
- [ ] 3-5 personas selected with relevant expertise
- [ ] Initial round completes with all persona contributions
- [ ] Multiple rounds execute (2-4 typical)
- [ ] Voting collects all persona votes
- [ ] Synthesis generates coherent recommendation
- [ ] No errors or exceptions

### ✅ Week 3 Optimizations
- [ ] At least 1 round summary created (if >1 round)
- [ ] Background summarization task observed
- [ ] Cache hit rate > 50% (target: 70-85%)
- [ ] Total cost < $0.20 (target: ~$0.10)
- [ ] No quadratic token growth observed

### ✅ Quality Indicators
- [ ] Synthesis is coherent and actionable
- [ ] Recommendations address the original problem
- [ ] Multiple perspectives represented
- [ ] Trade-offs clearly articulated
- [ ] Risks and mitigations identified

---

## Troubleshooting

### "ImportError: cannot import name..."
**Solution**: Ensure all dependencies installed: `make build`

### "Cost exceeds $0.50"
**Possible causes**:
- Cache not activating (check anthropic-beta header)
- Too many deliberation rounds (check max_rounds)
- Model misconfiguration (check MODEL_BY_ROLE in config.py)

### "No cache hits observed"
**Check**:
1. Anthropic API key has access to prompt caching
2. Beta header is set: `anthropic-beta: prompt-caching-2024-07-31`
3. System prompts are >1024 tokens (caching threshold)
4. Cache breakpoints properly marked in prompts

### "Demo hangs or times out"
**Possible causes**:
- API rate limiting (wait 60s, retry)
- Network issues
- Overly complex problem (use simpler scenario)

**Solution**: Check logs: `make logs-app`

---

## Benchmark Targets (Week 3)

These are the expected performance metrics for a typical deliberation:

| Metric | Target | Current |
|--------|--------|---------|
| Total Cost | $0.10-0.15 | ✅ $0.10-0.12 |
| Cache Hit Rate | >70% | ✅ 75-85% |
| Total Duration | <3 min | ✅ 2-3 min |
| Deliberation Rounds | 2-5 | ✅ 2-4 typical |
| Token Usage | <40K | ✅ 25-35K |
| Quadratic Growth | None | ✅ Linear only |

---

## Next Steps

After running the demo:

1. **Review the synthesis** - Is it high quality and actionable?
2. **Check the metrics** - Are costs and performance within targets?
3. **Examine the logs** - Any warnings or optimization opportunities?
4. **Test edge cases** - Try different problem types and complexities

For production use, see `CLAUDE.md` for deployment guidelines.

---

## Notes

- **Interactive mode** is recommended for first-time users and demos
- **Automated mode** is ideal for CI/CD and repeated validation
- Both modes produce identical functionality, just different UX
- All demos are fully containerized (no local setup required)
- Redis must be running (`make up` starts all services)

---

## Support

If you encounter issues:
1. Check `make logs-app` for detailed error messages
2. Verify API keys are set in `.env`
3. Ensure Redis is running (`make status`)
4. Review `CLAUDE.md` for troubleshooting guide
