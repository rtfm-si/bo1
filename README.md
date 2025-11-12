# Board of One (bo1)

AI-powered decision-making system that helps solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis using AI personas.

## Project Status

**v1 Development Phase** - Initial setup complete, implementation in progress.

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

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# 3. Start services
docker-compose up

# Or run in background
docker-compose up -d
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
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m scenario      # Scenario tests only

# Run with coverage
pytest --cov=bo1 --cov-report=html
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy bo1/

# Run all checks
ruff check . && ruff format --check . && mypy bo1/
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

- **Target**: <$1 per session
- **Haiku** for parallel expert calls (~$0.001-0.002 each)
- **Sonnet** for synthesis (~$0.006-0.01 each)
- **Prompt caching** for 90% cost reduction on repeated tokens

## Contributing

This is currently a development project. See [CLAUDE.md](./CLAUDE.md) for development guidelines.

## License

TBD
