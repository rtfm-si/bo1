# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Board of One (bo1)** is a console-based AI system that helps users solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis. The system simulates a board of domain experts using multiple AI personas to debate options and arrive at well-reasoned recommendations.

**Current Status**: v1 development in progress - project structure and configuration complete, core implementation pending

---

## Core Architecture

### System Flow

```
Problem Intake → Decomposition (1-5 sub-problems) → Expert Selection (3-5 personas)
→ Multi-Round Debate (adaptive rounds) → Voting → Synthesis → Final Recommendation
```

### Key Components

1. **Decomposer**: Breaks complex problems into 1-5 manageable sub-problems
2. **Persona Engine**: Selects 3-5 expert personas from pool of 35 pre-defined personas
3. **Deliberation Engine**: Manages multi-round debates with adaptive stopping
4. **Facilitator**: Orchestrates discussion, formulates options, synthesizes recommendations
5. **Moderators**: Conditional personas (Contrarian, Skeptic, Optimist) that intervene to improve debate quality
6. **Researcher**: On-demand evidence gathering (v1: LLM knowledge only)

---

## Technology Stack (v1)

| Component           | Technology                    | Notes                                                 |
| ------------------- | ----------------------------- | ----------------------------------------------------- |
| **Language**        | Python 3.12+                  | Latest stable with performance improvements           |
| **Package Manager** | uv                            | 10-100x faster than pip                               |
| **LLM**             | Claude Haiku 4.5 + Sonnet 4.5 | Haiku for parallel expert calls, Sonnet for synthesis |
| **Orchestration**   | LangChain (library mode)      | Prompt templates, caching, parallel execution         |
| **State**           | Redis                         | In-memory state, TTL support, LangChain integration   |
| **Embeddings**      | Voyage AI (voyage-3)          | Semantic similarity for convergence detection         |
| **Console UI**      | Rich                          | Beautiful terminal formatting, progress bars          |
| **Deployment**      | Docker Compose                | Redis + bo1 app containers                            |

---

## Important Files & Directories

### Documentation (zzz_important/)

- **`PRD.md`**: Complete product requirements with user stories, system flow, research findings
- **`IMPLEMENTATION_PROPOSAL.md`**: Detailed technical implementation plan (Python, LangChain, Redis, Voyage AI)
- **`PROMPT_ENGINEERING_FRAMEWORK.md`**: Comprehensive prompt engineering guidelines with XML templates, examples, chain-of-thought patterns
- **`CONSENSUS_BUILDING_RESEARCH.md`**: Research-backed techniques for convergence detection, stopping criteria, deadlock prevention
- **`TODO.md`**: Project task tracking

### Personas

- **`zzz_important/personas.json`**: 35 pre-defined expert personas with system prompts, traits, safety guidelines

### Configuration

- **`.env.example`**: Environment variables template (API keys, Redis config, cost limits)

---

## Key Design Principles

### 1. Adaptive Debate Length

- **Complexity-based rounds**: Simple (5 max), Moderate (7 max), Complex (10 max)
- **Early stopping**: Semantic convergence >0.85, novelty <0.3, conflict <0.2
- **Hard cap**: 15 rounds (prevents cognitive overload)
- **Research finding**: Most value in first 3-5 rounds; diminishing returns after 7-10

### 2. Problem Drift Prevention

- **#1 cause of failure**: Debate drifts from original sub-problem goal
- **Mitigation**: Show problem statement in every prompt, facilitator checks relevance, drift detection (score <6 triggers redirect)

### 3. Consensus Mechanisms

- **Simple majority**: Default for v1 (>50%)
- **Supermajority**: For one-way door decisions (≥75%)
- **Confidence calibration**: Experts reconsider confidence after seeing group votes
- **Disagree and commit**: Explicit commitment statement prevents endless relitigating

### 4. Quality Monitoring

- **Convergence**: Semantic similarity via Voyage AI embeddings
- **Novelty**: Each contribution scored vs. history (should decrease over time)
- **Conflict**: Opinion distribution tracking (0-1 scale)
- **Entropy**: Token diversity (high early = exploration, low late = convergence)

---

## Development Commands

### Setup

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY
# - VOYAGE_API_KEY
```

### Docker

```bash
# Start Redis + bo1 app
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f bo1

# Stop services
docker-compose down
```

### Development

```bash
# Run application
python -m bo1.main
# or with uv
uv run python -m bo1.main

# Run tests
pytest
# or with uv
uv run pytest

# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy bo1/

# Use Makefile for convenience
make help          # Show all available commands
make install-dev   # Install with dev dependencies
make test          # Run tests
make check         # Run all quality checks
```

---

## Code Structure (When Implemented)

```
bo1/
├── agents/
│   ├── base.py              # BaseAgent class (LangChain wrapper)
│   ├── expert.py            # ExpertPersona (Haiku 4.5)
│   ├── facilitator.py       # Facilitator (Sonnet 4.5)
│   ├── researcher.py        # Researcher (Haiku 4.5)
│   └── moderator.py         # Contrarian/Skeptic/Optimist
├── orchestration/
│   ├── session.py           # SessionOrchestrator
│   ├── deliberation.py      # DeliberationEngine
│   └── convergence.py       # Convergence metrics (Voyage AI)
├── models/
│   ├── problem.py           # Problem, SubProblem (Pydantic)
│   ├── persona.py           # PersonaProfile (from personas.json)
│   └── state.py             # SessionState (Redis-backed)
├── state/
│   ├── redis_manager.py     # Redis state management
│   └── serialization.py     # State serialization (JSON/Markdown)
├── prompts/
│   ├── templates/           # XML-based prompt templates
│   ├── examples/            # 2-3 examples per template
│   └── framework.py         # Prompt engineering framework
├── ui/
│   ├── console.py           # Rich-based console interface
│   └── prompts.py           # User input prompts
└── main.py                  # Entry point
```

---

## Common Patterns

### Parallel Expert Execution

```python
# Use asyncio.gather() for independent expert calls
contributions = await asyncio.gather(
    *[expert.contribute(prompt) for expert in experts]
)
```

### Sequential Facilitator Orchestration

```python
# Facilitator decides next action after each round
decision = await facilitator.decide_next_action(state)
if decision == "continue": # Next round
if decision == "vote":     # Force decision
if decision == "research": # Trigger researcher
```

### State Management

```python
# Save to Redis with TTL
await redis_manager.save_state(session_id, state)
await redis_manager.redis.expire(key, 86400)  # 24 hour TTL

# Export transcript
markdown = state.to_markdown()  # Human-readable
json_str = state.to_json()      # Machine-readable
```

---

## Testing Approach

### Unit Tests (Phase 1)

- Pydantic model validation
- Problem decomposition logic
- Persona selection algorithm
- Vote aggregation mechanisms

### Integration Tests (Phase 2)

- Full deliberation flow (problem → recommendation)
- Redis state persistence
- LangChain chain execution
- Convergence detection

### Scenario Tests (Phase 3)

- 10+ solopreneur scenarios from PRD
- Measure: time (5-15 min), cost (<$1), consensus (>70%)
- Edge cases: atomic problems, highly complex problems, deadlocks

---

## What's NOT in v1

**Deferred to v2**:

- Web interface (Svelte 5 + SvelteKit + FastAPI)
- Persistent sessions (pause/resume)
- PostgreSQL for long-term storage
- LangGraph for stateful workflows
- External research (web search)
- Custom user personas
- Authentication
- Multi-user/team collaboration

**v1 is console-only, single-user, session-based (no persistence beyond Redis TTL)**

---

## Key References

- **PRD**: Complete product requirements, user stories, system flow
- **Implementation Proposal**: Technical architecture, dependencies, deployment
- **Prompt Engineering Framework**: XML templates, examples, chain-of-thought patterns
- **Consensus Building Research**: Stopping criteria, convergence metrics, deadlock prevention
- **Personas JSON**: 35 pre-defined personas with system prompts and traits

---

## Notes for Claude Code

- **Always read PRD and Implementation Proposal** before making architectural decisions
- **Follow Prompt Engineering Framework** for all LLM prompts (XML structure, examples, thinking tags)
- **Use personas.json** as source of truth for persona attributes (don't hallucinate new personas)
- **Prioritize research-backed patterns** from Consensus Building Research (convergence detection, adaptive stopping)
- **v1 is console-only** - no web UI, no FastAPI, no database beyond Redis
- **Cost optimization is critical** - use Haiku for parallel calls, Sonnet only for synthesis
- **User sovereignty**: System provides recommendations, NOT directives ("We recommend..." not "You must...")
- **Safety first**: All personas have built-in safety guidelines to refuse harmful/illegal/unethical requests
