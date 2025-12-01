# End-to-End Meeting Tests

## Quick Start

```bash
# Run all E2E tests
pytest tests/integration/test_end_to_end_meeting.py -v -s

# Run single test with detailed logging
pytest tests/integration/test_end_to_end_meeting.py::test_complete_meeting_lifecycle -v -s --log-cli-level=INFO

# Run with cost tracking
pytest tests/integration/test_end_to_end_meeting.py -v -s --log-cli-level=INFO 2>&1 | tee test_run.log
```

## Prerequisites

### 1. Environment Variables

Ensure these are set in your `.env` file:

```bash
# API Keys (required)
ANTHROPIC_API_KEY=your_key_here
VOYAGE_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://bo1:password@localhost:5432/boardofone

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Cost Control (IMPORTANT!)
AI_OVERRIDE=true
AI_OVERRIDE_MODEL=claude-haiku-4-5-20251001
```

### 2. Services Running

```bash
# Start PostgreSQL and Redis
make up

# Or manually:
docker-compose -f docker-compose.infrastructure.yml up -d postgres redis
```

### 3. Database Migrations

```bash
# Apply migrations
uv run alembic upgrade head
```

## Test Suite Overview

### test_complete_meeting_lifecycle
- **Purpose**: Validates entire meeting flow from start to finish
- **Runtime**: 2-4 minutes
- **Cost**: ~$0.01-0.02 (with Haiku)
- **Validates**:
  - Problem decomposition (1-2 sub-problems)
  - Persona selection (3-5 experts)
  - Multi-round deliberation
  - Recommendation collection
  - Final synthesis
  - Database persistence
  - Event emission

### test_meeting_with_multiple_subproblems
- **Purpose**: Tests multi-sub-problem iteration logic
- **Runtime**: 4-6 minutes
- **Cost**: ~$0.02-0.03 (with Haiku)
- **Validates**:
  - Multiple sub-problem handling
  - next_subproblem transitions
  - sub_problem_results accumulation
  - Meta-synthesis generation

### test_meeting_convergence_triggers
- **Purpose**: Tests convergence detection and early stopping
- **Runtime**: 2-5 minutes
- **Cost**: ~$0.01-0.02 (with Haiku)
- **Validates**:
  - Convergence score calculation
  - Early stopping when consensus reached
  - Proper should_stop flag handling

## Expected Output

### Success
```
========================================
END-TO-END TEST SUMMARY
========================================
Session ID: e2e_test_20250112_143022
Execution Time: 142.3s
Sub-problems: 2
Experts: 4
Contributions: 12
Rounds: 2
Recommendations: 4
Synthesis Length: 1847 chars
Total Cost: $0.0234
Events (DB): 28
Events (Redis): 28
========================================
✅ ALL CHECKS PASSED
========================================

PASSED
```

### Failure Examples

**Missing synthesis:**
```
AssertionError: Synthesis should be generated
```

**Cost too high:**
```
AssertionError: assert 1.23 < 1.0
```

**Missing events:**
```
AssertionError: Missing event: decomposition_complete
```

## Cost Management

### Typical Costs (with AI_OVERRIDE=true, Haiku)
- Simple problem: $0.01-0.02
- Multi-sub-problem: $0.02-0.03
- Convergence test: $0.01-0.02
- **Total suite**: ~$0.04-0.07

### Without AI_OVERRIDE (Sonnet)
- Simple problem: $0.08-0.12
- Multi-sub-problem: $0.15-0.25
- Convergence test: $0.08-0.15
- **Total suite**: ~$0.30-0.50

⚠️ **Always use AI_OVERRIDE=true for testing!**

## Troubleshooting

### Redis Connection Refused
```bash
# Check Redis is running
docker ps | grep redis

# Start Redis if needed
docker-compose -f docker-compose.infrastructure.yml up -d redis
```

### PostgreSQL Connection Error
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Start PostgreSQL if needed
docker-compose -f docker-compose.infrastructure.yml up -d postgres

# Check database exists
docker exec -it boardofone-postgres-1 psql -U bo1 -d boardofone
```

### Test Timeout
```python
# Increase timeout in test file
pytestmark = [
    pytest.mark.timeout(900),  # Increase from 600 to 900 (15 minutes)
]
```

### High Costs
```bash
# Verify AI override is active
grep AI_OVERRIDE .env

# Should show:
# AI_OVERRIDE=true
# AI_OVERRIDE_MODEL=claude-haiku-4-5-20251001
```

### Missing Events in Database
```sql
-- Check events were saved
SELECT event_type, COUNT(*)
FROM session_events
WHERE session_id LIKE 'e2e_test_%'
GROUP BY event_type;

-- Check latest test session
SELECT *
FROM sessions
WHERE session_id LIKE 'e2e_test_%'
ORDER BY created_at DESC
LIMIT 1;
```

## Debug Mode

### Enable Verbose Logging
```bash
pytest tests/integration/test_end_to_end_meeting.py -v -s --log-cli-level=DEBUG
```

### Inspect State at Breakpoint
```python
# Add to test file
import pdb; pdb.set_trace()

# Then inspect:
print(json.dumps(final_state, indent=2, default=str))
```

### Check Redis Events Live
```bash
# In separate terminal, monitor Redis
redis-cli SUBSCRIBE "events:e2e_test_*"
```

## CI/CD Integration

### GitHub Actions
```yaml
e2e-tests:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: test
    redis:
      image: redis:7
  steps:
    - uses: actions/checkout@v3
    - name: Run E2E tests
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        AI_OVERRIDE: true
      run: |
        pytest tests/integration/test_end_to_end_meeting.py -v
```

## Performance Benchmarks

### Target Times (with Haiku)
- Decomposition: 5-10s
- Persona Selection: 3-8s
- Initial Round: 15-30s (3-5 experts in parallel)
- Follow-up Round: 10-20s
- Voting: 10-15s
- Synthesis: 8-15s
- **Total**: 60-150s

### If Tests Are Slow
1. Check AI_OVERRIDE is enabled (Sonnet is 5-10x slower)
2. Check parallel rounds are enabled (ENABLE_PARALLEL_ROUNDS=true)
3. Check network latency to Anthropic API
4. Check database connection pooling is working

## Next Steps

### Run Tests
```bash
pytest tests/integration/test_end_to_end_meeting.py -v -s --log-cli-level=INFO
```

### Review Results
- Check summary output for costs and timing
- Review logs for any warnings
- Verify all assertions passed

### Update Documentation
- Document any new failure modes
- Update cost estimates if changed
- Add new test cases as needed

## Questions?

See the full design document: `docs/END_TO_END_TEST_DESIGN.md`
