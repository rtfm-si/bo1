# Sprint Quick Reference Guide

**Quick access to key information for the 2-week optimization sprint**

---

## Sprint at a Glance

| Metric | Value |
|--------|-------|
| Duration | 10 working days (2 weeks) |
| Total Effort | 40-50 hours |
| Tasks | 8 major tasks + 7 quick wins |
| Expected ROI | 60-70% cost reduction |
| Code Reduction | 300+ lines |

---

## Daily Schedule

### Week 1: Foundation & Quick Wins

| Day | Hours | Focus | Deliverable |
|-----|-------|-------|-------------|
| Mon | 4-5h | Foundation | Test fixes + LLM cache start |
| Tue | 4-5h | Caching | LLM cache complete + Error handling |
| Wed | 4h | Standardization | Error handling complete |
| Thu | 5h | Quick Wins 1 | Compression, cache eviction, flags |
| Fri | 5-6h | Quick Wins 2 | SSE logging, bounds, rate limiting |

### Week 2: Advanced Features & Validation

| Day | Hours | Focus | Deliverable |
|-----|-------|-------|-------------|
| Mon | 4-6h | Refactoring | Event extractor pattern |
| Tue | 4-6h | Observability | Metrics collection |
| Wed | 5-7h | Advanced Cache | Persona selection caching |
| Thu | 3-4h | Integration | Testing & validation |
| Fri | 2-3h | Polish | Documentation & retrospective |

---

## Task Priority Matrix

### Critical (Do First)
1. **Test Collection Fixes** (Day 1, 1-2h) - Unblocks 28 tests
2. **Event Extractor Refactoring** (Day 6, 4-6h) - 32% code reduction

### High (High ROI)
3. **LLM Response Caching** (Day 1-2, 4-6h) - 60% cost savings
4. **Persona Selection Caching** (Day 8, 5-7h) - $200-400/month
5. **Error Handling** (Day 2-3, 3-4h) - Consistency across 28 endpoints

### Medium (Enablers)
6. **Metrics Collection** (Day 7, 4-6h) - Enables optimization
7. **Quick Wins Batch** (Day 4-5, 10-15h) - Multiple improvements
8. **Validation** (Day 9-10, 5-6h) - Quality assurance

---

## Command Cheatsheet

### Testing
```bash
# Quick test run
pytest -m "not requires_llm" -v

# Full test suite
make test

# Coverage report
pytest --cov=bo1 --cov=backend --cov-report=html

# Single test file
pytest tests/llm/test_cache.py -v
```

### Quality Checks
```bash
# All pre-commit checks
make pre-commit

# Individual checks
ruff check .
ruff format .
mypy bo1/ backend/
```

### Development
```bash
# Start services
make up

# View logs
make logs-api
make logs-frontend

# Shell access
make shell
```

### Git Workflow
```bash
# Feature branch
git checkout -b sprint-optimizations

# Conventional commits
git commit -m "feat: add LLM response caching"
git commit -m "fix: resolve test collection issues"
git commit -m "refactor: extract event data patterns"
git commit -m "docs: update sprint documentation"
```

---

## File Locations

### New Files Created
- `bo1/llm/cache.py` - LLM response caching
- `bo1/agents/persona_cache.py` - Persona selection caching
- `bo1/llm/embeddings.py` - Voyage AI embeddings
- `backend/api/utils/errors.py` - Error handling utilities
- `backend/api/event_extractors.py` - Event extraction framework
- `backend/api/metrics.py` - Metrics collection
- `backend/api/admin/metrics.py` - Metrics endpoint

### Modified Files
- `bo1/config.py` - Feature flags + cache settings
- `bo1/llm/broker.py` - Integrate LLM cache
- `bo1/agents/selector.py` - Integrate persona cache
- `bo1/graph/state.py` - Bounded state cache
- `backend/api/sessions.py` - Error handling + metrics
- `backend/api/control.py` - Error handling + metrics
- `backend/api/event_collector.py` - Refactored extractors
- `frontend/src/routes/(app)/meeting/[id]/+page.svelte` - Cache eviction

### Test Files
- `tests/llm/test_cache.py`
- `tests/agents/test_persona_cache.py`
- `tests/api/test_error_handling.py`
- `tests/api/test_event_extractors.py`
- `tests/api/test_metrics.py`
- `tests/api/test_compression.py`

---

## Configuration Variables

### Environment Variables to Add

```bash
# LLM Response Caching
ENABLE_LLM_RESPONSE_CACHE=true
LLM_RESPONSE_CACHE_TTL_SECONDS=86400  # 24 hours

# Persona Selection Caching
ENABLE_PERSONA_SELECTION_CACHE=true
VOYAGE_API_KEY=<your-voyage-api-key>

# Feature Flags
ENABLE_CONTEXT_COLLECTION=true
ENABLE_SSE_STREAMING=false  # Future

# Redis (already configured)
REDIS_URL=redis://:password@redis:6379/0

# Database (already configured)
DATABASE_URL=postgresql://bo1:password@postgres:5432/boardofone
```

---

## Success Metrics Tracking

### Quantitative Targets

| Metric | Baseline | Target | How to Measure |
|--------|----------|--------|----------------|
| Monthly LLM cost | $300-500 | $100-150 | Check LLM cache stats |
| Test coverage | 41% | 60%+ | `pytest --cov` |
| API error consistency | 60% | 95%+ | Code review |
| Code complexity | 884 lines | 600 lines | `wc -l event_collector.py` |
| LLM cache hit rate | 0% | 60%+ | Metrics endpoint |
| Persona cache hit rate | 0% | 40%+ | Metrics endpoint |

### Check Metrics

```bash
# API metrics
curl http://localhost:8000/api/admin/metrics \
  -H "X-Admin-Key: <admin-key>" | jq

# LLM cache stats
python -c "
from bo1.llm.cache import get_llm_cache
cache = get_llm_cache()
print(cache.get_stats())
"

# Persona cache stats
python -c "
from bo1.agents.persona_cache import get_persona_cache
cache = get_persona_cache()
print(cache.get_stats())
"
```

---

## Common Issues & Solutions

### Issue: Tests not collecting
**Solution:**
```bash
# Check pytest config
cat pyproject.toml | grep -A 10 "\[tool.pytest"

# Add asyncio marker
# See Task 1 in SPRINT_IMPLEMENTATION_PLAN.md
```

### Issue: LLM cache not working
**Solution:**
```bash
# Check environment variable
echo $ENABLE_LLM_RESPONSE_CACHE

# Check Redis connection
redis-cli -h localhost -p 6379 -a password ping

# View cache keys
redis-cli -h localhost -p 6379 -a password keys "llm:cache:*"
```

### Issue: Metrics endpoint 403
**Solution:**
```bash
# Ensure admin auth header
curl http://localhost:8000/api/admin/metrics \
  -H "X-Admin-Key: <your-admin-key>"

# Or use admin JWT token
```

### Issue: Pre-commit failing
**Solution:**
```bash
# Fix linting
ruff check . --fix

# Format code
ruff format .

# Fix type errors
mypy bo1/ backend/ --show-error-codes
```

---

## Rollback Procedures

### Task 2: LLM Response Caching
```bash
# Disable via environment variable
export ENABLE_LLM_RESPONSE_CACHE=false

# Or revert commit
git log --oneline | grep "LLM response caching"
git revert <commit-hash>
```

### Task 3: Error Handling
```bash
# Remove decorators
# Restore try/except blocks from git history
git show <commit-hash>^:backend/api/sessions.py > sessions.py.backup
```

### Task 5: Event Extractor Refactoring
```bash
# Revert entire refactoring
git log --oneline | grep "event extractor"
git revert <commit-hash>
```

### Task 7: Persona Selection Caching
```bash
# Disable via environment variable
export ENABLE_PERSONA_SELECTION_CACHE=false

# Or revert commit
git revert <commit-hash>
```

---

## Key Contacts & Resources

### Documentation
- Full Plan: `SPRINT_IMPLEMENTATION_PLAN.md`
- Week 2 Details: `SPRINT_IMPLEMENTATION_PLAN_WEEK2.md`
- Project Docs: `CLAUDE.md`

### External APIs
- Voyage AI: https://www.voyageai.com/
- Anthropic: https://console.anthropic.com/

### Monitoring
- Metrics Endpoint: `GET /api/admin/metrics`
- Redis UI: `http://localhost:8081` (if running)
- Database: `psql -U bo1 -h localhost boardofone`

---

## Sprint Milestones

### End of Week 1 Checkpoint
- [ ] Test collection fixed (28 tests running)
- [ ] LLM response caching implemented and tested
- [ ] Error handling standardized across API
- [ ] 7 quick wins completed
- [ ] All Week 1 tasks committed

### End of Week 2 Checkpoint
- [ ] Event extractor refactored (32% reduction)
- [ ] Metrics collection functional
- [ ] Persona selection caching implemented
- [ ] All tests passing (60%+ coverage)
- [ ] Sprint summary documented

### Deployment Readiness
- [ ] All feature flags configured
- [ ] Environment variables documented
- [ ] Rollback procedures tested
- [ ] Performance benchmarks recorded
- [ ] Ready for staging deployment

---

## Quick Decision Guide

### Should I implement a feature?
✅ **Yes** if:
- Listed in sprint plan
- Unblocks other tasks
- High ROI (cost/performance)

❌ **No** if:
- Not in sprint scope
- Can wait for next sprint
- Low priority/impact

### Should I optimize code?
✅ **Yes** if:
- Part of task requirements
- Improves readability
- Reduces duplication

❌ **No** if:
- Not related to task
- Premature optimization
- Increases complexity

### Should I add tests?
✅ **Yes** if:
- New functionality
- Complex logic
- High-risk code

❌ **Skip** if:
- Simple getter/setter
- Already covered
- Time-constrained

---

## Emergency Contacts

### Blockers
- **Redis down:** Check `make status`, restart with `make up`
- **Database issues:** Check connection with `psql -U bo1 -h localhost`
- **Tests failing:** Run `make test` for full output, fix one file at a time
- **Build broken:** Check `make logs-api` and `make logs-frontend`

### Help Resources
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Project README: `README.md`
- Testing Guide: `docs/TESTING.md`
- Docker Guide: `docs/DOCKER.md`

---

**Last Updated:** Sprint Start
**Next Review:** End of Week 1 (Day 5)
**Final Review:** End of Sprint (Day 10)
