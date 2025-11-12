# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Board of One (bo1)** is a console-based AI system that helps users solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis. The system simulates a board of domain experts using multiple AI personas to debate options and arrive at well-reasoned recommendations.

**Current Status**: Design complete, ready for implementation (v1 console application)

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

| Component | Technology | Notes |
|-----------|-----------|-------|
| **Language** | Python 3.12+ | Latest stable with performance improvements |
| **Package Manager** | uv | 10-100x faster than pip |
| **LLM** | Claude Haiku 4.5 + Sonnet 4.5 | Haiku for parallel expert calls, Sonnet for synthesis |
| **Orchestration** | LangChain (library mode) | Prompt templates, caching, parallel execution |
| **State** | Redis | In-memory state, TTL support, LangChain integration |
| **Embeddings** | Voyage AI (voyage-3) | Semantic similarity for convergence detection |
| **Console UI** | Rich | Beautiful terminal formatting, progress bars |
| **Deployment** | Docker Compose | Redis + bo1 app containers |

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

**Note**: Implementation not yet started. Commands below are for planned setup.

### Setup (Planned)
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
# (Requires pyproject.toml - not yet created)
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY
# - VOYAGE_API_KEY
```

### Docker (Planned)
```bash
# Start Redis + bo1 app
# (Requires docker-compose.yml - not yet created)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f bo1

# Stop services
docker-compose down
```

### Development (Planned)
```bash
# Run application
python -m bo1.main

# Run tests
pytest

# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy bo1/
```

---

## Critical Implementation Guidelines

### Prompt Engineering (MUST READ: PROMPT_ENGINEERING_FRAMEWORK.md)

**Golden Rules**:
1. **Explicit > Implicit**: Clear instructions, not vague requests
2. **Show, Don't Tell**: 2-3 concrete examples > 500 words of abstract instructions
3. **Structure Everything**: Use XML tags for complex prompts
4. **Make Thinking Visible**: `<thinking>` tags for reasoning before responses
5. **Chain Complex Workflows**: Break multi-step processes into sequential subtasks

**Template Structure** (all prompts):
```xml
<system_role>Define persona/role</system_role>

<instructions>Clear, specific task</instructions>

<examples>
  <example>
    <user_input>...</user_input>
    <output>...</output>
  </example>
  <!-- 2-3 examples optimal -->
</examples>

<thinking>
Request step-by-step reasoning
</thinking>

<output_format>
Structured format (XML/JSON)
</output_format>
```

### Persona System Prompts
- Load from `zzz_important/personas.json`
- Each persona has: name, archetype, category, description, traits, temperature, system_prompt, safety_guidelines
- **Critical Question Guidelines**: Only ask blocking questions for essential missing information
- **Safety Protocol**: Built into every persona - refuse harmful/illegal/unethical requests

### Cost Optimization
- **Target**: <$1 per session (3-5 sub-problems)
- **Per sub-problem**: $0.05-0.15
- **Haiku** for parallel expert calls (~$0.001-0.002 each)
- **Sonnet** for synthesis/facilitation (~$0.006-0.01 each)
- **Prompt caching**: Cache persona system prompts, problem statement, history (90% cost reduction on cached tokens)
- **Kill switch**: Max $1.00 per session

### Convergence Detection (Voyage AI)
```python
# Semantic similarity of recent contributions
convergence = calculate_semantic_convergence(state)
# Should increase over time (start <0.4, end >0.85)

# Novelty of new contributions vs. history
novelty = calculate_novelty_score(contribution, history)
# Should decrease over time (start >0.6, end <0.3)

# Early stop when: convergence >0.85 AND novelty <0.3 AND conflict <0.2
```

### Deadlock Prevention
1. **Circular argument detection**: Same arguments repeating 3+ times
2. **Conflict scoring**: Sustained >0.8 conflict for 5+ rounds
3. **Moderator triggers**: Contrarian (premature consensus), Skeptic (unverified claims), Optimist (excessive negativity)
4. **Force resolution**: Skip to voting if deadlock persists

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

## Quality Benchmarks (v1 Success Criteria)

### Functional
- ✓ Decomposes 90% of test problems
- ✓ Generates actionable recommendations
- ✓ Completes typical session in 5-15 minutes
- ✓ Surfaces trade-offs in 100% of recommendations
- ✓ Adaptive stopping works (30-40% early stop rate)

### Quality
- ✓ Consensus level: >70% for clear decisions
- ✓ Average confidence: >0.7 for final votes
- ✓ Problem drift: <10% of deliberations
- ✓ Cost: <$1 per session
- ✓ Time: 2-4 minutes per sub-problem

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

## Common Development Tasks

### Adding a New Persona
1. Edit `old_docs/personas.json`
2. Add entry with: code, name, archetype, category, description, traits, system_prompt, temperature
3. Include safety_guidelines and critical_question_guidelines
4. Set is_active=true, is_visible=true
5. Test with persona selection algorithm

### Creating a Prompt Template
1. Create XML file in `prompts/templates/`
2. Include: system_role, instructions, examples (2-3), thinking section, output_format
3. Add metadata comment (version, date, performance metrics)
4. Test with actual LLM calls
5. Consider A/B testing variant

### Tuning Convergence Thresholds
1. Run 20+ deliberations with current settings
2. Log metrics: convergence, novelty, conflict, rounds_used
3. Analyze: Are we stopping too early? Too late?
4. Adjust thresholds in `orchestration/convergence.py`
5. Re-test and measure impact

---

## Research-Backed Best Practices

### Debate Rounds
- **3-5 rounds**: Optimal for most problems
- **7-10 rounds**: Maximum before diminishing returns
- **>15 rounds**: Cognitive overload risk (agents lose track)

### Moderator Interventions
- **Early (rounds 1-4)**: Trigger Contrarian if premature consensus (>80% agreement before round 3)
- **Middle (rounds 5-7)**: Trigger Skeptic for unverified claims
- **Late (rounds 8-10)**: Trigger Optimist if deadlocked or excessively negative

### LLM Agent Limitations
- **Stanford finding**: Pure LLM agents are "excessively polite and cooperative" - need explicit disagreement mechanisms
- **Society of Mind**: Divergent thinking valuable EARLY, convergent thinking valuable LATE
- **Problem drift**: ~0.8% of debates suffer from drifting off-topic (prevention critical)

---

## Troubleshooting

### Debate runs too long
- Check: Are convergence thresholds too strict? (lower convergence_threshold to 0.8)
- Check: Is problem drift happening? (review relevance_scores)
- Check: Are max_rounds set appropriately for complexity? (reduce for simple problems)

### Poor recommendation quality
- Check: Are personas relevant to problem domain? (review selection algorithm)
- Check: Is problem decomposition clear? (review sub-problem goals)
- Check: Are prompts providing enough context? (review persona system prompts)
- Check: Are examples in prompts high-quality? (add/improve examples)

### High costs
- Check: Is prompt caching enabled? (verify cache_control in LangChain calls)
- Check: Are we using Haiku for parallel calls? (verify model selection)
- Check: Is early stopping working? (check early_stop_triggered metrics)
- Check: Are max_rounds too high? (reduce for simple problems)

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
