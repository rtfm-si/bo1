# Board of One (bo1)

AI-powered decision-making system that helps solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis using AI personas.

## Project Status

**v1 Development Phase** - Week 1 foundation complete (Days 1-6), Day 7 integration testing in progress.

### Week 1 Progress (Days 1-7)
- ✅ Core Pydantic models (Problem, Persona, State, Votes)
- ✅ LLM client with prompt caching (90% cost reduction)
- ✅ Redis state management with serialization
- ✅ Console UI with Rich formatting
- ✅ 45 expert personas catalog
- ✅ Modular prompt composition system
- 🚧 Week 1 integration tests

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (recommended)
- API Keys:
  - [Anthropic API](https://console.anthropic.com/) (Claude)
  - [Voyage AI API](https://www.voyageai.com/) (Embeddings)

### Installation

#### Option 1: Docker (Recommended)

```bash
# 1. Clone and navigate to repository
cd bo1

# 2. Initial setup (creates .env, directories)
make setup

# 3. Edit .env and add your API keys
# Required: ANTHROPIC_API_KEY, VOYAGE_API_KEY

# 4. Build and start services
make build
make up

# 5. Run application
make run
```

#### Option 2: Local Development

```bash
# 1. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment and install dependencies
uv sync

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# 4. Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# 5. Run application
uv run python -m bo1.main
```

## Development

### Running Tests

```bash
# Docker (recommended)
make test              # All tests
make test-unit         # Unit tests only

# Local environment
pytest                              # All tests
pytest -m unit                      # Unit tests only
pytest -m integration               # Integration tests only
pytest -m "not requires_llm"        # Skip tests requiring API keys

# Run Week 1 integration test
pytest tests/test_integration_day7.py -v

# Run with coverage
pytest --cov=bo1 --cov-report=html
```

### Code Quality

```bash
# Docker (recommended)
make lint              # Run linter (ruff check)
make format            # Run formatter (ruff format)
make check             # Run lint + typecheck

# Local environment
ruff check bo1/ tests/                           # Linting
ruff format bo1/ tests/                          # Formatting
mypy bo1/ --ignore-missing-imports               # Type checking

# Run all checks
ruff check bo1/ tests/ && ruff format --check bo1/ tests/ && mypy bo1/ --ignore-missing-imports
```

### Project Structure

```
bo1/
├── bo1/                    # Main application package
│   ├── agents/            # Agent implementations (Expert, Facilitator, etc.)
│   ├── orchestration/     # Deliberation engine & session management
│   ├── models/            # Pydantic models (Problem, Persona, State)
│   ├── state/             # Redis state management
│   ├── prompts/           # Prompt templates and framework
│   ├── ui/                # Console UI (Rich)
│   ├── config.py          # Configuration management
│   └── main.py            # Application entry point
├── tests/                 # Test suite
├── zzz_important/         # Documentation & design specs
│   ├── PRD.md
│   ├── IMPLEMENTATION_PROPOSAL.md
│   ├── PROMPT_ENGINEERING_FRAMEWORK.md
│   ├── CONSENSUS_BUILDING_RESEARCH.md
│   └── personas.json      # 35 pre-defined expert personas
├── docker-compose.yml     # Docker services configuration
├── Dockerfile             # Application container
└── pyproject.toml         # Python package configuration
```

## Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Developer guide for working with this codebase
- **[PRD.md](./zzz_important/PRD.md)** - Product requirements & user stories
- **[Implementation Proposal](./zzz_important/IMPLEMENTATION_PROPOSAL.md)** - Technical architecture
- **[Prompt Engineering Framework](./zzz_important/PROMPT_ENGINEERING_FRAMEWORK.md)** - AI prompt guidelines
- **[Consensus Building Research](./zzz_important/CONSENSUS_BUILDING_RESEARCH.md)** - Research-backed techniques

## Architecture

### System Flow

```
Problem Intake → Decomposition (1-5 sub-problems) → Expert Selection (3-5 personas)
→ Multi-Round Debate (adaptive rounds) → Voting → Synthesis → Final Recommendation
```

### Prompt Engineering Framework

Board of One uses a **modular composition** approach for AI prompts:

#### 3-Layer Composition
```
Final Prompt = BESPOKE IDENTITY + GENERIC PROTOCOLS + DYNAMIC CONTEXT
```

1. **Bespoke Identity** (from `personas.json`)
   - Unique system role for each of 45 experts
   - ~879 characters average per persona
   - Examples: "You are Maria Chen, a growth hacker..."

2. **Generic Protocols** (from `reusable_prompts.py`)
   - `BEHAVIORAL_GUIDELINES`: Communication norms
   - `EVIDENCE_PROTOCOL`: Reasoning standards
   - `COMMUNICATION_PROTOCOL`: XML output format
   - `SECURITY_PROTOCOL`: Safety guardrails
   - **Cached for 90% cost reduction**

3. **Dynamic Context** (per request)
   - Problem statement
   - Participant list
   - Current phase (initial_round, discussion, voting)
   - Previous contributions (hierarchical summaries)

#### Why This Matters
- **DRY**: Generic protocols reused across all personas
- **Caching**: Protocols + problem statement cached = massive savings
- **Maintainability**: Update protocols once, affects all personas
- **Consistency**: All personas follow same behavioral norms

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.12+ | Core implementation |
| Package Manager | uv | Fast dependency management |
| LLM | Claude Haiku 4.5 + Sonnet 4.5 | AI reasoning |
| Orchestration | LangChain | LLM workflow management |
| State | Redis | In-memory session state |
| Embeddings | Voyage AI | Semantic similarity |
| Console UI | Rich | Beautiful terminal output |

## Cost Optimization

Board of One achieves ~$0.10 per deliberation through:

### Prompt Caching (90% savings)
- Generic protocols (BEHAVIORAL_GUIDELINES, EVIDENCE_PROTOCOL) are cached
- Problem statements cached across all persona calls
- Round summaries cached across subsequent rounds
- **Sonnet with caching** is cheaper than Haiku without!

### Model Allocation
| Role | Model | Rationale |
|------|-------|-----------|
| Personas | Sonnet 4.5 + cache | Complex reasoning, high reuse |
| Facilitator | Sonnet 4.5 | Orchestration requires reasoning |
| Summarizer | Haiku 4.5 | Simple compression task |
| Decomposer | Sonnet 4.5 | Complex problem analysis |
| Moderators | Haiku 4.5 | Simple interventions |

### Hierarchical Context
- **Old rounds**: 100-token summaries (cached)
- **Current round**: Full messages (uncached)
- **Total context**: ~1,400 tokens (linear growth, not quadratic)
- **Async summarization**: Zero latency impact (runs in background)

### Target Costs (Per Deliberation)
- 35 persona contributions (Sonnet + cache): ~$0.095
- 6 round summaries (Haiku): ~$0.007
- Facilitator decisions (Sonnet): ~$0.003
- **Total**: ~$0.10 per deliberation (70% cheaper than naive implementation)

## Contributing

This is currently a development project. See [CLAUDE.md](./CLAUDE.md) for development guidelines.

## License

TBD
