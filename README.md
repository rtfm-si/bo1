# Board of One (bo1)

AI-powered decision-making system that helps solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis using AI personas.

## Project Status

**v2 Deployed to Production** - Live at [https://boardof.one](https://boardof.one)

### Current State
- ✅ Console application (v1) - LangGraph-based multi-agent deliberation
- ✅ Web API (v2) - FastAPI with SSE streaming (polling-based)
- ✅ SuperTokens Auth - OAuth (Google/GitHub/LinkedIn)
- ✅ Production deployment - Blue-green with automated SSL
- ✅ PostgreSQL + pgvector - Persistent storage with embeddings
- ✅ Redis checkpointing - Session state management
- ✅ 45 expert personas - Modular prompt composition
- ✅ Closed beta mode - Email whitelist validation

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

## API Documentation

- **[openapi.json](./openapi.json)** - Full OpenAPI specification (includes admin endpoints)
- **[openapi-public.json](./openapi-public.json)** - Public API specification (excludes admin endpoints)
- **[SSE Events](./docs/SSE_EVENTS.md)** - Server-Sent Events schema contracts

Generate specs with:
```bash
make openapi-export     # Full spec
make openapi-public     # Public spec (no admin endpoints)
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

## API Reference

Board of One provides a comprehensive RESTful API for programmatic access to deliberation sessions.

### Starting the API

```bash
# Docker (recommended)
make up               # Start all services (Redis, PostgreSQL, API)

# Access API endpoints
# Base URL: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

The API runs on port 8000 by default. Use the Swagger UI at `/docs` for interactive API exploration.

### API Endpoints

#### Health Checks
- `GET /api/health` - Overall system health
- `GET /api/health/redis` - Redis connection status
- `GET /api/health/db` - PostgreSQL connection status
- `GET /api/health/anthropic` - Anthropic API status

#### Session Management
- `POST /api/v1/sessions` - Create new deliberation session
- `GET /api/v1/sessions` - List all sessions (with pagination)
- `GET /api/v1/sessions/{session_id}` - Get session details

#### Deliberation Control
- `POST /api/v1/sessions/{session_id}/start` - Start deliberation
- `POST /api/v1/sessions/{session_id}/pause` - Pause running deliberation
- `POST /api/v1/sessions/{session_id}/resume` - Resume paused deliberation
- `POST /api/v1/sessions/{session_id}/kill` - Terminate deliberation
- `POST /api/v1/sessions/{session_id}/clarify` - Submit clarification answer

#### Real-time Streaming
- `GET /api/v1/sessions/{session_id}/stream` - SSE stream for live updates

#### Context Management
- `GET /api/v1/context` - Get user business context
- `PUT /api/v1/context` - Update user business context
- `DELETE /api/v1/context` - Delete user business context

#### Admin Endpoints (Requires X-Admin-Key header)
- `GET /api/admin/sessions/active` - List all active sessions
- `GET /api/admin/sessions/{session_id}/full` - Get full session state
- `POST /api/admin/sessions/{session_id}/kill` - Admin kill session
- `POST /api/admin/sessions/kill-all` - Kill all active sessions
- `GET /api/admin/research-cache/stats` - Research cache statistics
- `GET /api/admin/research-cache/stale` - List stale cache entries
- `DELETE /api/admin/research-cache/{cache_id}` - Delete cache entry

### Example Usage

```bash
# Create a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "problem_statement": "Should we invest $500K in expanding to the European market?",
    "problem_context": {"budget": 500000, "current_market": "North America"}
  }'

# Start deliberation
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/start

# Stream real-time updates (Server-Sent Events)
curl -N http://localhost:8000/api/v1/sessions/{session_id}/stream

# Get session details
curl http://localhost:8000/api/v1/sessions/{session_id}
```

### Performance Metrics

The API has been tested for production readiness:
- **Concurrent Sessions**: Handles 10+ simultaneous deliberations without conflicts
- **Response Times**: Average <500ms for all endpoints
- **SSE Streaming**: Currently polling-based (2s intervals); full real-time implementation planned (see STREAMING_IMPLEMENTATION_PLAN.md)
- **Connection Stability**: >95% stable connections under load

For detailed API documentation and performance benchmarks, see:
- **[Week 6 API Summary](./zzz_project/WEEK6_API_SUMMARY.md)** - Complete API reference
- **OpenAPI Specification**: http://localhost:8000/openapi.json

### Performance Testing

```bash
# Test concurrent session management (10 sessions)
python scripts/test_concurrent_sessions.py

# Test SSE streaming scalability (50 clients)
python scripts/test_sse_scalability.py

# Custom tests
python scripts/test_concurrent_sessions.py --sessions 20 --api-url http://localhost:8000
python scripts/test_sse_scalability.py --clients 100
```

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
