# Running Board of One (Current State: Days 8-11)

The current implementation includes **Problem Decomposition** and **Persona Selection & Initial Round**. Here's how to run it:

## Prerequisites

1. **Docker environment running**:
   ```bash
   make up
   ```

2. **Environment variables set** (`.env` file with API keys):
   - `ANTHROPIC_API_KEY`
   - `VOYAGE_API_KEY` (optional for current demo)
   - `REDIS_URL`

## Option 1: Run Demo Script (Recommended)

This demonstrates the full Days 8-11 flow:

```bash
# Inside Docker container
make shell
python test_current_state.py
```

**What it does:**
1. **Problem Decomposition**: Analyzes "Should I invest $50K in SEO or paid ads?" and breaks it into sub-problems
2. **Persona Selection**: Recommends 3-5 expert personas based on the problem domain
3. **Initial Round**: Runs parallel contributions from all selected personas
4. **Displays**: Rich formatted output with contributions, costs, and metrics

**Expected output:**
- Sub-problems table with complexity scores
- Selected personas with justifications
- Parallel expert contributions
- Total cost: ~$0.10-0.20
- Total time: ~30-60 seconds

## Option 2: Interactive Python Session

For manual testing and experimentation:

```bash
make shell
python
```

```python
import asyncio
from bo1.agents.decomposer import DecomposerAgent
from bo1.ui.console import Console

# Initialize
console = Console()
decomposer = DecomposerAgent()

# Test decomposition
decomposition = decomposer.decompose_problem(
    problem_description="Should I hire a co-founder or stay solo?",
    context="Technical founder, 6 months in, $200K ARR",
    constraints=["Budget: $150K"]
)

# Display results
console.print_decomposition(decomposition)

# Validate
is_valid, errors = decomposer.validate_decomposition(decomposition)
print(f"Valid: {is_valid}")
```

## Option 3: Run Integration Tests

To verify everything works without making LLM calls (uses mocks):

```bash
make test-unit
```

To run full integration tests with real LLM calls:

```bash
make test-integration
```

## Current Capabilities

✅ **Working:**
- Problem decomposition (1-5 sub-problems)
- Complexity scoring (1-10)
- Dependency mapping
- User review flow (approve/modify)
- Persona recommendation (LLM-based)
- Parallel initial round execution
- Prompt caching for cost optimization
- State management (Redis)
- Rich console UI

❌ **Not Yet Implemented:**
- Multi-round deliberation (Days 12-13)
- Voting & synthesis (Day 14)
- Cost optimization features (Week 3)
- Convergence detection (Week 4)
- Full end-to-end pipeline

## Cost Estimate

Running the demo script costs approximately:
- **Decomposition**: ~$0.01 (Sonnet call)
- **Persona Selection**: ~$0.01 (Sonnet call)
- **Initial Round (5 personas)**: ~$0.10-0.15 (Sonnet with caching)
- **Total per demo run**: ~$0.12-0.17

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
```bash
# Check your .env file
cat .env | grep ANTHROPIC_API_KEY

# If missing, add it:
echo "ANTHROPIC_API_KEY=your-key-here" >> .env
make down && make up
```

**"Redis connection refused"**
```bash
# Restart Redis
make down
make up
make redis-cli  # Test connection
```

**"Import errors"**
```bash
# Reinstall dependencies
make shell
uv sync
```

## Next Steps

After verifying Days 8-11 work:
1. Implement **Multi-Round Deliberation** (Days 12-13)
2. Add **Voting & Synthesis** (Day 14)
3. Optimize with **Hierarchical Context** (Week 3)
4. Add **Convergence Detection** (Week 4)

See `zzz_project/TASKS.md` for full roadmap.
