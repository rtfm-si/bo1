# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project: Board of One (bo1)

Console-based AI system using multi-agent deliberation (Claude personas) to solve complex problems through structured debate and synthesis.

**Status**: v1 development - Docker-first architecture, core implementation in progress

---

## System Flow

```
Problem → Decomposition (1-5 sub-problems) → Persona Selection (3-5 experts)
→ Multi-Round Debate → Voting → Synthesis → Recommendation
```

---

## Commands (Docker-First Workflow)

```bash
# Setup (one-time)
make setup           # Creates .env, directories
make build           # Build Docker images
make up              # Start Redis + app containers

# Development
make run             # Run deliberation (interactive)
make shell           # Bash in container
make logs-app        # View app logs

# Testing
make test            # All tests in container
make test-unit       # Unit tests only

# Code Quality
make lint            # ruff check
make format          # ruff format
make check           # lint + typecheck

# Redis
make redis-cli       # Open Redis CLI
make redis-ui        # Web UI (http://localhost:8081)
```

**Hot Reload**: Edit code locally, changes immediately available in container (no rebuild).

---

## Architecture Specifics

### Prompt Engineering (Critical)

All prompts follow `zzz_important/PROMPT_ENGINEERING_FRAMEWORK.md`:
- **XML structure** with `<thinking>`, `<contribution>` tags
- **Modular composition**: Bespoke persona identity + generic protocols + dynamic context
- Personas stored in `bo1/data/personas.json` (45 experts)
- Generic protocols in `bo1/prompts/reusable_prompts.py`

**Cost Optimization**:
- Use **Sonnet 4.5 with prompt caching** for personas (90% cheaper than naive)
- Use **Haiku 4.5** for summarization (background agent)
- Hierarchical context: Old rounds = 100-token summaries, current round = full messages
- Target: ~$0.10 per deliberation (35 persona calls + 6 summaries)

### Context Management (Prevents Quadratic Growth)

```python
# Previous rounds: Summarized (cached)
round_summaries: list[str]  # 100 tokens each

# Current round: Full detail (uncached)
current_round_contributions: list[dict]  # ~200 tokens each

# Total context: ~1,400 tokens (linear growth, not quadratic)
```

**Summarizer Agent**: Runs in background (asyncio) while next round proceeds. Zero latency impact.

### Consensus Mechanisms

- **Convergence detection**: Semantic similarity >0.85, novelty <0.3 → early stop
- **Adaptive rounds**: Simple (5 max), Moderate (7), Complex (10), Hard cap (15)
- **Problem drift detection**: #1 failure cause - check relevance every contribution
- **Facilitator orchestration**: Sequential decisions (continue/vote/research/moderator)

---

## Key Files

- `bo1/data/personas.json` - 45 experts (ONLY bespoke `<system_role>`, 879 chars avg)
- `bo1/prompts/reusable_prompts.py` - Generic protocols (behavioral, evidence, communication)
- `bo1/prompts/summarizer_prompts.py` - Background summarization (Haiku)
- `zzz_project/TASKS.md` - 28-day implementation roadmap (83 tasks)
- `zzz_important/CONSENSUS_BUILDING_RESEARCH.md` - Research-backed stopping criteria

---

## Important Design Constraints

**v1 is console-only**:
- No FastAPI, no web UI, no PostgreSQL
- Redis for session state (24h TTL)
- LangChain as library (NOT LangGraph)

**Cost targets**:
- $0.10-0.15 per sub-problem deliberation
- 5-15 min per deliberation
- 60-70% cost reduction via prompt caching

**User sovereignty**:
- System provides recommendations, NOT directives
- "We recommend X" not "You must do X"

**Safety**:
- All personas refuse harmful/illegal/unethical requests
- Generic safety protocol in `reusable_prompts.py`

---

## Common Patterns

### Persona Prompt Composition

```python
from bo1.prompts.reusable_prompts import compose_persona_prompt

# Compose: BESPOKE + DYNAMIC + GENERIC
system_prompt = compose_persona_prompt(
    persona_system_role=persona["system_prompt"],  # From personas.json
    problem_statement="Should we invest $500K...",
    participant_list="Maria, Zara, Tariq",
    current_phase="discussion"
)
```

### Parallel Expert Calls (Initial Round)

```python
# All personas contribute simultaneously
contributions = await asyncio.gather(
    *[call_persona(code) for code in persona_codes]
)
```

### Hierarchical Context Building

```python
# Build context for Round N
context = {
    "round_summaries": state.round_summaries,  # Rounds 1 to N-2 (cached)
    "current_round": state.current_round_contributions  # Round N-1 (full detail)
}
```

---

## Testing Strategy

1. **Unit**: Pydantic models, prompt composition, vote aggregation
2. **Integration**: Redis persistence, LLM mocks, convergence detection
3. **Scenario**: 10+ solopreneur problems from PRD (5-15 min, <$1, >70% consensus)

---

## What NOT to Do

- Don't create new personas (use existing 45 from `personas.json`)
- Don't add web UI features (v2 only)
- Don't use LangGraph (too heavy for v1)
- Don't hardcode prompts (use composition functions)
- Don't ignore cost optimization (prompt caching is critical)
- Don't let context grow quadratically (use hierarchical summarization)
