# Board of One (bo1) - Implementation Proposal

**Version**: 1.0
**Date**: 2025-01-11
**Status**: Draft for Review

---

## Executive Summary

This document proposes specific implementation decisions for Board of One (bo1) v1, a console-based AI system that helps users solve complex problems through multi-agent debate and synthesis.

**Key Recommendations:**

- **Language**: Python 3.12+ (latest stable with performance improvements)
- **LLM Provider**: Anthropic Claude (Haiku 4.5 + Sonnet 4.5)
- **Architecture**: LangChain-based orchestration with custom deliberation logic
- **Console UI**: Rich library for progressive text UI
- **State Management**: Redis for in-memory state + JSON export
- **Package Management**: uv (modern, fast Python package manager)
- **Embeddings**: Voyage AI (optimized for retrieval and similarity)
- **Prompt Engineering**: Structured framework with XML tags, examples, and chain-of-thought

---

## 1. Language & Core Stack

### Decision: Python 3.12+

**Rationale:**

- Latest stable Python with performance improvements (PEP 709 comprehension inlining, improved error messages)
- Best ecosystem for LLM integration (anthropic SDK, langchain)
- Strong async support (asyncio) for parallel agent calls
- Excellent AI tooling ecosystem
- Rich console UI libraries (Rich, Textual)

**Package Management: uv**

Modern Python package manager (replacement for pip/pip-tools):
- **10-100x faster** than pip
- Built-in virtual environment management
- Reproducible installs with lockfiles
- Drop-in replacement for pip commands

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init bo1
cd bo1

# Add dependencies
uv add anthropic langchain langchain-anthropic
uv add redis voyageai
uv add rich pydantic python-dotenv
```

**Core Dependencies:**

```toml
[project]
name = "bo1"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    # LLM & Orchestration
    "anthropic>=0.39.0",          # Claude API client
    "langchain>=0.3.0",            # LLM orchestration library
    "langchain-anthropic>=0.3.0",  # Anthropic integration
    "langchain-community>=0.3.0",  # Redis cache, utilities

    # State & Embeddings
    "redis>=5.0.0",                # State management & LLM caching
    "voyageai>=0.2.0",             # Embeddings API

    # Data & Config
    "pydantic>=2.0.0",             # Data validation
    "python-dotenv>=1.0.0",        # Environment config

    # Console UI
    "rich>=13.0.0",                # Beautiful console output

    # Utilities
    "numpy>=1.26.0",               # Array operations (cosine similarity)
    "scikit-learn>=1.3.0",         # Cosine similarity calculations
    "scipy>=1.11.0",               # Statistical tests (A/B testing)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.6.0",                 # Fast linter/formatter
    "mypy>=1.11.0",                # Type checking
]

# v2 dependencies (web interface - NOT in v1)
web = [
    "fastapi>=0.115.0",            # Web API framework
    "uvicorn>=0.32.0",             # ASGI server
    "langgraph>=0.2.0",            # Stateful agent orchestration
]
```

**Dependency Notes:**

- **NO FastAPI in v1**: Console-only, no web interface (PRD section 10)
- **NO LangGraph in v1**: Too heavy for simple orchestration, consider for v2
- **LangChain as library**: Use for prompt templates, caching, parallel execution
- **Redis**: Required for state + LLM response caching (cost optimization)

**Alternative Considered**: TypeScript
- Pro: Type safety, modern async/await
- Con: Less mature LLM tooling, smaller ecosystem for AI/ML
- Verdict: Python 3.12+ with mypy provides type safety + better AI ecosystem

---

## 2. LLM Provider & Model Strategy

### Decision: Anthropic Claude (Haiku 4.5 + Sonnet 4.5)

**Model Allocation:**

| Role            | Model          | Rationale                                   | Est. Cost/Call |
| --------------- | -------------- | ------------------------------------------- | -------------- |
| Expert Personas | **Haiku 4.5**  | Parallel calls, debate contributions        | ~$0.001-0.002  |
| Facilitator     | **Sonnet 4.5** | Complex synthesis, option formulation       | ~$0.006-0.01   |
| Researcher      | **Haiku 4.5**  | Knowledge retrieval, simple summaries       | ~$0.001-0.002  |
| Decomposer      | **Sonnet 4.5** | Complex problem analysis                    | ~$0.01-0.02    |
| Moderators      | **Haiku 4.5**  | Contrarian/skeptic/optimist interventions   | ~$0.001-0.002  |

**Target Cost**: $0.05-0.15 per sub-problem (within PRD spec)

**Why Claude 4.5 Models:**
- **Haiku 4.5**: Latest fast model with improved instruction-following
- **Sonnet 4.5**: State-of-the-art reasoning for complex synthesis
- Superior prompt adherence (critical for persona consistency)
- Better structured output compliance (XML tags, JSON mode)

**API Strategy via LangChain:**

```python
from langchain_anthropic import ChatAnthropic

# Configure models
haiku = ChatAnthropic(
    model="claude-haiku-4-5-20241022",
    temperature=0.7,
    max_tokens=2048
)

sonnet = ChatAnthropic(
    model="claude-sonnet-4-5-20250514",
    temperature=0.7,
    max_tokens=4096
)

# Parallel execution
from langchain.runnables import RunnableParallel
parallel_personas = RunnableParallel(
    expert1=persona1_chain,
    expert2=persona2_chain,
    expert3=persona3_chain
)
```

**Prompt Caching (Critical for Cost):**
- Cache persona system prompts (reused across all turns)
- Cache problem statement + discussion history
- 90% cost reduction on cached tokens
- LangChain supports Anthropic's prompt caching natively

**Alternative Considered**: OpenAI GPT-4o
- Pro: Lower cost per token
- Con: Inferior instruction-following for structured outputs, weaker prompt adherence
- Verdict: Claude 4.5 superior for persona consistency and structured prompts

**Future Enhancement**: Multi-provider support (v2)

---

## 3. Multi-Agent Architecture

### Decision: LangChain + Custom Deliberation Logic

**Why LangChain?**

- **Prompt Management**: Built-in support for templates, caching, structured outputs
- **LLM Abstraction**: Easy model switching (Haiku ↔ Sonnet)
- **Parallel Execution**: RunnableParallel for concurrent expert calls
- **Memory/State**: Redis integration for conversation history
- **Not Opinionated**: Use LangChain as library, not framework - custom orchestration for deliberation
- **Mature Ecosystem**: Well-maintained, extensive docs, active community

**Why NOT LangGraph/AutoGen/CrewAI for v1?**

- **LangGraph**:
  - Designed for complex stateful agent graphs with cycles, branches, human-in-loop
  - Overkill for v1 console app (linear flow: intake → decompose → deliberate → vote → synthesize)
  - Better suited for v2 web interface with pause/resume, user interventions, streaming
  - Adds complexity without benefit for simple sequential orchestration
  - **Decision**: Defer to v2 when adding web UI + streaming

- **AutoGen**:
  - Microsoft-owned, OpenAI-centric design patterns
  - Complex multi-agent abstractions not aligned with our debate mechanics

- **CrewAI**:
  - Too opinionated about agent roles (manager/worker patterns)
  - Less flexible for custom deliberation flow

**v1 Orchestration Strategy:**

Simple Python classes + LangChain chains:
```python
class DeliberationOrchestrator:
    """Simple sequential orchestrator for v1"""

    async def run_deliberation(self, problem: str) -> Recommendation:
        # 1. Decompose
        sub_problems = await self.decomposer.decompose(problem)

        # 2. Select personas
        personas = await self.selector.select_experts(sub_problems)

        # 3. For each sub-problem
        for sub in sub_problems:
            # 4. Multi-round debate (custom logic)
            transcript = await self.debate_engine.run_debate(sub, personas)

            # 5. Vote
            votes = await self.vote_processor.collect_votes(personas, transcript)

            # 6. Synthesize
            result = await self.facilitator.synthesize(sub, votes)

        # 7. Final recommendation
        return await self.facilitator.final_synthesis(results)
```

**Why this works for v1:**
- Linear flow, no complex branching
- Redis state sufficient (no checkpointing mid-flow needed)
- Simple to understand, debug, and test
- LangChain provides chains, prompts, caching - that's all we need

**v2 upgrade path:**
- Add LangGraph when we need: streaming, pause/resume, human-in-loop, complex branching
- Current architecture easily migrates to LangGraph nodes

**Custom Architecture:**

```
┌─────────────────────────────────────────────┐
│          Session Orchestrator               │
│  - Problem intake                           │
│  - Sub-problem sequencing                   │
│  - User checkpoints                         │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│       Deliberation Engine                   │
│  - Round management                         │
│  - Convergence monitoring                   │
│  - Early stopping logic                     │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Expert 1 │ │ Expert 2 │ │ Expert N │  (Parallel async calls)
│ (Haiku)  │ │ (Haiku)  │ │ (Haiku)  │
└──────────┘ └──────────┘ └──────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│          Facilitator (Sonnet)               │
│  - Summarize rounds                         │
│  - Formulate options                        │
│  - Synthesize recommendations               │
└─────────────────────────────────────────────┘
```

**Implementation Pattern:**

- **Persona classes**: `ExpertPersona`, `Facilitator`, `Researcher`
- Each persona wraps Claude API with role-specific system prompts
- **Orchestrator**: State machine managing flow (intake → decompose → deliberate → vote → synthesize)
- **Parallel execution**: `asyncio.gather()` for independent expert calls
- **Sequential execution**: Await facilitator before next round

**Code Structure:**

```
bo1/
├── agents/
│   ├── base.py           # BaseAgent class (LangChain wrapper)
│   ├── expert.py         # ExpertPersona (LangChain chain)
│   ├── facilitator.py    # Facilitator (Sonnet 4.5)
│   ├── researcher.py     # Researcher (Haiku 4.5)
│   └── moderator.py      # Contrarian/Skeptic/Optimist
├── orchestration/
│   ├── session.py        # SessionOrchestrator
│   ├── deliberation.py   # DeliberationEngine
│   └── convergence.py    # Convergence metrics (Voyage AI)
├── models/
│   ├── problem.py        # Problem, SubProblem (Pydantic)
│   ├── persona.py        # PersonaProfile (35 personas)
│   └── state.py          # SessionState (Redis-backed)
├── state/
│   ├── redis_manager.py  # Redis state management
│   └── serialization.py  # State serialization
├── prompts/
│   ├── templates/        # XML-based prompt templates
│   ├── examples/         # 3-5 examples per template
│   └── framework.py      # Prompt engineering framework
├── ui/
│   ├── console.py        # Rich-based console interface
│   └── prompts.py        # User input prompts
└── main.py               # Entry point
```

**LangChain Integration Pattern:**

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_community.cache import RedisCache
from langchain.globals import set_llm_cache
import redis

# Configure Redis caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)
set_llm_cache(RedisCache(redis_client))

# Persona chain with structured prompts
persona_prompt = ChatPromptTemplate.from_messages([
    ("system", "{persona_system_prompt}"),
    ("human", "<problem>{problem_statement}</problem>\n\n<discussion_history>{history}</discussion_history>\n\n<thinking>\nYour private reasoning:\n</thinking>\n\n<contribution>\nYour statement to the group:\n</contribution>")
])

persona_chain = persona_prompt | haiku | StructuredOutputParser()
```

---

## 4. State Management

### Decision: Redis for In-Memory State + Pydantic Models + JSON Export

**Why Redis?**

- **Fast in-memory storage**: Sub-millisecond read/write for session state
- **TTL support**: Auto-expire sessions after completion (e.g., 24 hours)
- **Persistence options**: Optional RDB/AOF for durability
- **LangChain integration**: Built-in Redis memory/cache support
- **Simple deployment**: Single Redis instance sufficient for v1
- **Structured data**: Hash/JSON support for complex state

**State Architecture:**

```python
# Redis key structure
# session:{session_id}:state -> Full SessionState (JSON)
# session:{session_id}:messages -> List of debate messages
# session:{session_id}:metrics -> Convergence metrics per round
# llm_cache:{hash} -> LangChain LLM response cache

import redis.asyncio as redis
from redis.commands.json.path import Path

class RedisStateManager:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

    async def save_state(self, session_id: str, state: SessionState):
        """Save session state to Redis"""
        key = f"session:{session_id}:state"
        await self.redis.json().set(
            key,
            Path.root_path(),
            state.model_dump()
        )
        await self.redis.expire(key, 86400)  # 24 hour TTL

    async def load_state(self, session_id: str) -> SessionState:
        """Load session state from Redis"""
        key = f"session:{session_id}:state"
        data = await self.redis.json().get(key)
        return SessionState(**data)
```

**State Structure:**

```python
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class SubProblemStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class SubProblem(BaseModel):
    id: str
    goal: str
    context: str
    complexity: int  # 1-10
    dependencies: List[str]  # IDs of prerequisite sub-problems
    max_rounds: int  # Calculated from complexity
    status: SubProblemStatus = SubProblemStatus.PENDING

class PersonaProfile(BaseModel):
    name: str
    title: str
    background: str
    expertise_domain: str
    risk_tolerance: float  # 0-1 (conservative → aggressive)
    time_horizon: str  # "short-term" | "long-term"
    perspective: str  # "optimistic" | "pessimistic" | "neutral"
    approach: str  # "analytical" | "intuitive" | "balanced"

class DebateContribution(BaseModel):
    round: int
    speaker: str  # Persona name or "FACILITATOR"
    content: str
    timestamp: float
    novelty_score: Optional[float] = None

class Vote(BaseModel):
    expert: str
    option: str
    rationale: str
    confidence: float  # 0-1
    calibrated_confidence: Optional[float] = None

class SubProblemResult(BaseModel):
    sub_problem_id: str
    options: List[dict]  # [{label, pros, cons, best_if}, ...]
    votes: List[Vote]
    recommendation: str
    confidence: float
    rounds_used: int
    early_stop_triggered: bool
    quality_metrics: dict

class SessionState(BaseModel):
    problem_statement: str
    clarifications: List[dict]
    sub_problems: List[SubProblem]
    expert_roster: List[PersonaProfile]
    debate_transcript: List[DebateContribution]
    sub_problem_results: List[SubProblemResult]
    final_recommendation: Optional[str] = None
    session_start: float
    session_end: Optional[float] = None

    def to_json(self) -> str:
        """Export session to JSON"""
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        """Export session as markdown transcript"""
        # Implementation to format as readable markdown
        pass
```

**Why Redis (not PostgreSQL/SQLite)?**

- **Speed**: In-memory performance critical for real-time deliberation
- **Simplicity**: No schema migrations, just key-value + JSON
- **LangChain native**: Built-in integration for caching and memory
- **TTL**: Auto-cleanup of old sessions
- **v1 scope**: No complex queries needed, Redis sufficient
- **v2 path**: Can add Postgres for long-term storage, keep Redis for hot state

**Export Capability:**

- After session completion: `session.to_json()` → save to file
- Markdown transcript: `session.to_markdown()` → human-readable format
- Redis persistence: Optional RDB snapshots for backup

**Docker Deployment:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: bo1-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  bo1:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: bo1-app
    depends_on:
      redis:
        condition: service_healthy
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - VOYAGE_API_KEY=${VOYAGE_API_KEY}
    volumes:
      - ./bo1:/app/bo1
      - ./prompts:/app/prompts
      - ./personas.json:/app/personas.json
    stdin_open: true
    tty: true
    command: python -m bo1.main

volumes:
  redis-data:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Run application
CMD ["python", "-m", "bo1.main"]
```

**Why Docker for Everything:**
- **Reproducible environment**: Same setup across dev/staging/prod
- **Easy onboarding**: `docker-compose up` gets everything running
- **Isolated services**: Redis in its own container
- **Version control**: Docker images for rollback
- **Local development**: Matches production environment

---

## 5. Problem Decomposition

### Decision: LLM-Based Decomposition with Sonnet

**Approach:**

- Use Claude Sonnet with structured output (JSON mode or strict prompting)
- Single API call: problem statement → sub-problems + dependencies + complexity

**Prompt Strategy:**

```python
DECOMPOSITION_PROMPT = """
You are an expert problem decomposer. Analyze this problem and break it into 1-5 sub-problems.

PROBLEM:
{problem_statement}

CONTEXT:
{clarifications}

OUTPUT FORMAT (JSON):
{
  "sub_problems": [
    {
      "goal": "Clear statement of what needs to be decided/resolved",
      "context": "Constraints, resources, success criteria",
      "complexity": 5,  // 1-10 scale
      "dependencies": []  // IDs of prerequisite sub-problems (empty if parallel)
    }
  ]
}

RULES:
- 1 sub-problem: Atomic problem (no decomposition needed)
- 2-5 sub-problems: Standard range (optimal)
- If >5 identified: Group into 3-5 meta-problems
- Complexity 1-3: Simple (binary choice, low ambiguity)
- Complexity 4-6: Moderate (multiple factors, some ambiguity)
- Complexity 7-10: Complex (many factors, high ambiguity, one-way door)
- Dependencies: Use array of IDs ([] if parallel, ["sub_1"] if depends on sub_1)
"""
```

**Validation:**

- Parse JSON response
- Validate 1-5 sub-problems (reject if violated)
- Check dependency graph for cycles
- Assign max_rounds based on complexity (PRD section 3.2)

**User Review:**

- Present decomposition in console
- Allow edit/merge/add sub-problems
- Confirm before proceeding

---

## 6. Expert Persona Selection

### Decision: 35-Persona Pool + LLM-Based Matching

**Persona Pool (v1):**

Maintain library of **35 pre-defined personas** covering diverse domains and perspectives:

**Why 35 personas?**
- Comprehensive domain coverage (technology, business, operations, risk, human factors)
- Diverse perspectives within each domain (conservative/aggressive, short/long-term)
- Sufficient variety for complex multi-faceted problems
- Manageable for LLM selection (fits in context window)
- Allows 5-8 expert selection with minimal overlap

```python
PERSONA_POOL = [
    PersonaProfile(
        name="Dr. Sarah Chen",
        title="Technical Architect",
        background="20 years building scalable systems, led engineering at 2 unicorns",
        expertise_domain="technical",
        risk_tolerance=0.4,  # Conservative
        time_horizon="long-term",
        perspective="neutral",
        approach="analytical"
    ),
    PersonaProfile(
        name="Marcus Johnson",
        title="Financial Analyst",
        background="Former CFO, specialized in startup runway optimization",
        expertise_domain="financial",
        risk_tolerance=0.3,  # Conservative
        time_horizon="short-term",
        perspective="pessimistic",
        approach="analytical"
    ),
    # ... 10-13 more personas covering:
    # - User Advocate
    # - Risk Manager
    # - Growth Strategist
    # - Operations Expert
    # - Behavioral Psychologist
    # - Data Scientist
    # - Marketing Strategist
    # - Legal/Compliance Expert
    # - Product Manager
    # - Sales Expert
]
```

**Selection Algorithm:**

```python
async def select_experts(
    problem: str,
    sub_problems: List[SubProblem],
    pool: List[PersonaProfile]
) -> List[PersonaProfile]:
    """
    Use LLM to select 3-5 experts from pool based on problem domains
    """
    prompt = f"""
    Given this problem and sub-problems, select 3-5 experts from the pool.

    PROBLEM: {problem}
    SUB-PROBLEMS: {[sp.goal for sp in sub_problems]}

    AVAILABLE EXPERTS:
    {[f"{p.name} - {p.title} ({p.expertise_domain})" for p in pool]}

    SELECT 3-5 experts ensuring:
    - Domain coverage (technical, financial, market, operations, risk, human)
    - Perspective diversity (optimist + pessimist)
    - Risk tolerance mix (conservative + moderate)
    - Time horizon balance (short-term + long-term)

    OUTPUT (JSON): {{"selected": ["Dr. Sarah Chen", "Marcus Johnson", ...]}}
    """

    response = await call_claude_sonnet(prompt)
    selected_names = parse_json(response)["selected"]

    # Return matching personas from pool
    return [p for p in pool if p.name in selected_names]
```

**Persona Storage (Existing Data):**

```python
# Load from old_docs/personas.json
# Schema from reference.personas table:
{
    "code": "growth_hacker",              # Unique identifier
    "name": "Zara Morales",               # Full name
    "archetype": "Growth Hacker",         # Display title
    "category": "marketing",              # Domain category
    "description": "Zara brings growth experimentation expertise...",
    "emoji": "📈",
    "traits": {
        "creative": 0.9,
        "analytical": 0.7,
        "optimistic": 0.8,
        "risk_averse": 0.2,
        "detail_oriented": 0.4
    },
    "system_prompt": "<persona_identity>You are Zara Morales...</persona_identity>",
    "temperature": 0.85,
    "response_style": "technical",        # analytical, socratic, technical, etc.
    "domain_expertise": ["technical", "strategic"]
}
```

**Your Existing 35 Personas (old_docs/personas.json):**
- Growth Hacker (Zara Morales) - Marketing
- Financial Strategist (Maria Santos) - Finance
- Risk Officer (Ahmad Hassan) - Legal/Risk
- Wellness Advisor (Dr. Kenji Nakamura) - Wellness
- No-Code Builder (Quinn Beaumont) - Tech
- Corporate Strategist (Henrik Sørensen) - Strategy
- ... 29 more personas

**Key Advantages:**
- ✅ **Pre-built system prompts**: Each persona has carefully crafted identity
- ✅ **Safety guidelines**: Built-in security protocol in every persona
- ✅ **Trait diversity**: Balanced analytical/creative, risk-averse/optimistic
- ✅ **Question guidelines**: CRITICAL QUESTION GUIDELINES prevent over-questioning
- ✅ **Temperature settings**: Per-persona temperature for style consistency

**Implementation:**

```python
import json
from pathlib import Path

class PersonaLoader:
    def __init__(self):
        self.personas = self._load_personas()

    def _load_personas(self) -> dict:
        """Load 35 personas from old_docs/personas.json"""
        path = Path("old_docs/personas.json")
        with path.open() as f:
            data = json.load(f)
            # Extract from "select * from reference.personas" array
            return {p["code"]: p for p in data["select * from reference.personas"]}

    def get_persona(self, code: str) -> dict:
        """Get persona by code"""
        return self.personas[code]

    def get_active_personas(self) -> list[dict]:
        """Get all active, visible personas"""
        return [p for p in self.personas.values()
                if p["is_active"] and p["is_visible"]]
```

**Why Pre-Defined Pool (Not Dynamic)?**

- **Consistent quality**: Pre-vetted personas with balanced attributes
- **System prompts included**: Each persona has production-ready prompt
- **Safety built-in**: Security protocol in every persona
- **Faster execution**: No LLM call to generate personas
- **35 is optimal**: Large enough for diversity, small enough for selection
- v2 can add dynamic generation or user-custom personas

---

## 7. Debate Mechanics & Convergence

### Decision: Voyage AI Embeddings + Rule-Based Stopping

**Why Voyage AI?**

- **Optimized for retrieval**: State-of-the-art embeddings for semantic similarity
- **Better than sentence-transformers**: Superior performance on similarity tasks
- **API-based**: No local model loading, faster startup
- **Cost-effective**: $0.00012 per 1K tokens (negligible for convergence checks)
- **Research-backed**: Used in production RAG systems

**Convergence Metrics:**

```python
import voyageai

class ConvergenceMonitor:
    def __init__(self):
        self.client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        self.model = "voyage-3"  # Latest model
        self.history = []

    def calculate_metrics(self, contributions: List[str]) -> dict:
        """
        Calculate convergence metrics for current round using Voyage AI
        """
        # Get embeddings from Voyage AI
        result = self.client.embed(
            contributions,
            model=self.model,
            input_type="document"  # Optimized for semantic similarity
        )
        embeddings = np.array(result.embeddings)

        # Semantic similarity (convergence)
        pairwise_similarity = cosine_similarity(embeddings)
        avg_similarity = pairwise_similarity.mean()

        # Novelty score (vs. all previous contributions)
        if self.history:
            # Embed all history for comparison
            history_result = self.client.embed(
                self.history,
                model=self.model,
                input_type="document"
            )
            historical_embeddings = np.array(history_result.embeddings)
            current_embedding = embeddings.mean(axis=0)
            novelty = 1 - cosine_similarity(
                [current_embedding],
                historical_embeddings
            ).max()
        else:
            novelty = 1.0  # First round always novel

        # Conflict score (opinion distribution)
        # Variance in semantic positions
        conflict = pairwise_similarity.std()

        self.history.extend(contributions)

        return {
            "convergence": float(avg_similarity),
            "novelty": float(novelty),
            "conflict": float(conflict)
        }
```

**Cost Analysis:**
- Typical round: 5 experts × 150 words = ~750 tokens
- Voyage cost: $0.00012 / 1K tokens = ~$0.00009 per round
- 10 rounds = $0.0009 (negligible vs. LLM costs)

**Stopping Criteria:**

```python
def should_stop_debate(
    round: int,
    max_rounds: int,
    metrics: dict,
    min_rounds: int = 3
) -> tuple[bool, str]:
    """
    Determine if debate should stop early

    Returns: (should_stop, reason)
    """
    # Hard limits
    if round >= max_rounds:
        return True, "max_rounds_reached"

    if round >= 15:  # Cognitive overload hard cap
        return True, "cognitive_overload_cap"

    # Must complete minimum rounds
    if round < min_rounds:
        return False, ""

    # Early stop - consensus reached
    if (metrics["convergence"] > 0.85 and
        metrics["novelty"] < 0.3 and
        metrics["conflict"] < 0.2):
        return True, "consensus_reached"

    # Early stop - diminishing returns
    # (Check if last 2 rounds had low novelty)
    if (metrics["novelty"] < 0.3 and
        hasattr(metrics, "previous_novelty") and
        metrics["previous_novelty"] < 0.3):
        return True, "diminishing_returns"

    # Intervention - deadlock
    if metrics["conflict"] > 0.8 and round > 5:
        return False, "deadlock_intervention_needed"

    return False, ""
```

**Why Voyage AI (vs sentence-transformers)?**

| Criteria | Voyage AI | sentence-transformers |
|----------|-----------|----------------------|
| **Quality** | State-of-the-art (voyage-3) | Good (all-MiniLM-L6-v2) |
| **Setup** | API call (no local model) | Download 80MB model |
| **Speed** | API latency (~100ms) | Local inference (~50ms) |
| **Cost** | $0.0009 per 10 rounds | Free (local compute) |
| **Maintenance** | Zero (API updated) | Manual model updates |
| **Verdict** | **Better for v1** | Consider for v2 if cost-sensitive |

**Alternative Considered**: Rule-based only (keyword overlap)
- Pro: Zero cost, simple logic
- Con: Misses semantic similarity ("reduce costs" vs "cut expenses")
- Verdict: Embeddings essential for quality convergence detection

---

## 8. Facilitator Interventions

### Decision: Rule-Based Triggers + LLM-Generated Interventions

**Moderator Personas (Conditional):**

```python
class ModeratorType(str, Enum):
    CONTRARIAN = "contrarian"
    SKEPTIC = "skeptic"
    OPTIMIST = "optimist"

def check_intervention_needed(
    round: int,
    metrics: dict,
    contributions: List[DebateContribution]
) -> Optional[ModeratorType]:
    """
    Determine if moderator intervention needed
    """
    # Contrarian: Premature consensus in early rounds
    if round <= 3 and metrics["convergence"] > 0.8:
        return ModeratorType.CONTRARIAN

    # Skeptic: Unverified claims detection (simple heuristic)
    # Look for absolute statements without caveats
    if round in [4, 5, 6]:  # Middle rounds
        recent = contributions[-3:]  # Last 3 contributions
        if any("definitely" in c.content or "always" in c.content
               for c in recent):
            return ModeratorType.SKEPTIC

    # Optimist: Excessive negativity / deadlock
    if round > 7 and metrics["conflict"] > 0.8:
        return ModeratorType.OPTIMIST

    return None
```

**Moderator System Prompts:**

```python
CONTRARIAN_PROMPT = """
You are the Contrarian moderator. The group is converging too quickly (round {round}).
Your role: Challenge the consensus, surface overlooked risks, propose alternatives.

CURRENT CONSENSUS: {consensus_summary}

Provide a 100-word contrarian perspective that:
- Questions unstated assumptions
- Highlights potential downsides
- Suggests alternative framing
"""

SKEPTIC_PROMPT = """
You are the Skeptic moderator. You notice unverified claims being made.

RECENT CLAIMS: {recent_contributions}

Challenge these claims (100 words):
- Ask for evidence
- Question certainty
- Probe edge cases
"""

OPTIMIST_PROMPT = """
You are the Optimist moderator. The debate is deadlocked or excessively negative.

CURRENT STALEMATE: {summary}

Break the deadlock (100 words):
- Find common ground
- Reframe problem constructively
- Suggest hybrid solutions
"""
```

**Problem Drift Detection:**

```python
def calculate_drift_score(
    sub_problem_goal: str,
    recent_contributions: List[str],
    model: SentenceTransformer
) -> float:
    """
    Calculate how far discussion has drifted from sub-problem goal

    Returns: Relevance score 0-10 (10 = perfectly on-topic)
    """
    goal_embedding = model.encode([sub_problem_goal])
    contribution_embeddings = model.encode(recent_contributions)

    similarities = cosine_similarity(goal_embedding, contribution_embeddings)
    avg_relevance = similarities.mean()

    # Scale to 0-10
    return float(avg_relevance * 10)

# Usage in round loop
drift_score = calculate_drift_score(sub_problem.goal, recent_contributions, model)
if drift_score < 6:
    facilitator_redirect = await facilitator.redirect_discussion(
        sub_problem.goal,
        recent_contributions
    )
```

---

## 9. Voting & Synthesis

### Decision: LLM-Based Option Formulation + Simple Majority (v1)

**Option Formulation (Facilitator):**

```python
OPTION_FORMULATION_PROMPT = """
Based on this debate transcript, formulate 2-4 distinct options.

DEBATE TRANSCRIPT:
{transcript}

OUTPUT (JSON):
{
  "options": [
    {
      "label": "Option A: Clear name",
      "description": "1-2 sentence description",
      "pros": ["Advantage 1", "Advantage 2", "Advantage 3"],
      "cons": ["Disadvantage 1", "Disadvantage 2"],
      "best_if": "Conditions where this is optimal"
    }
  ]
}

RULES:
- 2-4 options (2 = simple binary, 3-4 = complex)
- Options must be DISTINCT (not minor variations)
- Options should represent actual positions from debate
- Balanced pros/cons (2-3 each)
"""
```

**Voting Process:**

```python
async def conduct_vote(
    experts: List[ExpertPersona],
    options: List[dict],
    debate_transcript: str
) -> List[Vote]:
    """
    Parallel voting: Each expert votes independently
    """
    vote_tasks = [
        expert.vote(options, debate_transcript)
        for expert in experts
    ]

    votes = await asyncio.gather(*vote_tasks)

    # Confidence calibration (PRD 4.3)
    calibrated_votes = await calibrate_confidence(votes, experts)

    return calibrated_votes

async def calibrate_confidence(
    votes: List[Vote],
    experts: List[ExpertPersona]
) -> List[Vote]:
    """
    Show all votes to experts, allow confidence recalibration
    """
    calibration_tasks = [
        expert.calibrate_confidence(expert_vote, all_votes)
        for expert, expert_vote in zip(experts, votes)
    ]

    calibrated = await asyncio.gather(*calibration_tasks)
    return calibrated
```

**Vote Aggregation (v1: Simple Majority):**

```python
def aggregate_votes(votes: List[Vote]) -> dict:
    """
    v1: Simple majority voting
    v2: Add reversibility detection + adaptive mechanism
    """
    from collections import Counter

    vote_counts = Counter(v.option for v in votes)
    winner = vote_counts.most_common(1)[0][0]

    # Calculate consensus level
    consensus = vote_counts[winner] / len(votes)

    # Average confidence
    avg_confidence = sum(v.calibrated_confidence or v.confidence
                        for v in votes) / len(votes)

    return {
        "winner": winner,
        "vote_distribution": dict(vote_counts),
        "consensus_level": consensus,
        "average_confidence": avg_confidence
    }
```

**Synthesis:**

```python
SYNTHESIS_PROMPT = """
Synthesize the final recommendation for this sub-problem.

SUB-PROBLEM GOAL: {goal}
OPTIONS: {options}
VOTES: {votes}
VOTE RESULT: {aggregation}

Provide recommendation (200-300 words):
1. State recommended option clearly
2. Explain reasoning (refer to vote distribution + argument strength)
3. Acknowledge dissenting views respectfully
4. State confidence level
5. Highlight key caveats/conditions

Use advisory language: "We recommend..." NOT "You must..."
"""
```

---

## 10. Console Interface

### Decision: Rich Library with Progressive Disclosure

**Why Rich?**

- Beautiful console UI with colors, formatting, progress bars
- Markdown rendering support
- Tree/panel layouts for structured content
- Active maintenance, good docs

**UI Components:**

```python
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown
from rich.tree import Tree

console = Console()

# Welcome screen
console.print(Panel.fit(
    "[bold blue]Board of One (bo1)[/bold blue]\n"
    "Expert debate system for complex decisions",
    border_style="blue"
))

# Expert roster display
tree = Tree("[bold]Expert Board[/bold]")
for expert in experts:
    tree.add(f"[yellow]{expert.name}[/yellow] - {expert.title}")
console.print(tree)

# Debate round display
console.print(Panel(
    f"[bold cyan]ROUND {round}/{max_rounds}[/bold cyan]\n\n"
    f"[yellow]{expert.name}:[/yellow] {contribution}",
    title=f"Sub-Problem {i+1}/{total}",
    border_style="cyan"
))

# Progress indicator
with Progress() as progress:
    task = progress.add_task("[cyan]Deliberating...", total=max_rounds)
    # Update as rounds progress
    progress.update(task, advance=1)

# User checkpoint
continue_debate = Confirm.ask(
    "Continue to next round?",
    choices=["yes", "skip-to-vote", "intervene"],
    default="yes"
)
```

**Verbosity Levels (v1: Standard only):**

- v1: Show all contributions (standard verbosity)
- v2: Add concise (summaries only) and detailed (include metrics)

**Streaming vs. Batch:**

- v1: Batch (show full round after all experts respond)
- v2: Stream (show contributions as they complete) - requires async UI updates

---

## 11. Research Integration (v1)

### Decision: LLM Knowledge Only, Manual Detection

**Research Request Detection:**

```python
def detect_research_request(contribution: str) -> Optional[str]:
    """
    Simple pattern matching for research requests
    """
    patterns = [
        r"I(?:'d)? need (?:research|data|information) (?:on|about) (.+)",
        r"(?:Can|Could) (?:we|someone) research (.+)\?",
        r"I(?:'d)? like to (?:know|understand) more about (.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, contribution, re.IGNORECASE)
        if match:
            return match.group(1)  # Research topic

    return None

# Usage in round
for contribution in round_contributions:
    topic = detect_research_request(contribution.content)
    if topic and research_count < 2:  # Max 2 per sub-problem
        research_result = await researcher.research(topic)
        # Include in next round context
        research_count += 1
```

**Researcher Persona:**

```python
RESEARCHER_PROMPT = """
You are a Research assistant. Provide evidence-based information on this topic.

TOPIC: {topic}
CONTEXT: {sub_problem_goal}

Provide research summary (150-200 words):
- Key facts/data from your knowledge base
- Relevant considerations
- Caveats/limitations

Source: Your training knowledge (as of Jan 2025). No external search.
"""
```

**v2 Enhancement:**

- Add web search integration (Tavily, Exa)
- Add structured data sources (APIs, databases)

---

## 12. Cost Management & Optimization

### Decision: Token Budgeting + Streaming Responses

**Token Budget Tracking:**

```python
class CostTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Anthropic pricing (Jan 2025)
        self.HAIKU_INPUT = 0.25 / 1_000_000
        self.HAIKU_OUTPUT = 1.25 / 1_000_000
        self.SONNET_INPUT = 3.00 / 1_000_000
        self.SONNET_OUTPUT = 15.00 / 1_000_000

    def track_call(self, model: str, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_cost(self) -> float:
        # Simplified: assumes mixed usage
        return (self.total_input_tokens * self.HAIKU_INPUT +
                self.total_output_tokens * self.HAIKU_OUTPUT)

    def check_budget(self, max_cost: float = 1.0) -> bool:
        """Prevent runaway costs"""
        return self.get_cost() < max_cost
```

**Context Window Management:**

```python
def prepare_debate_context(
    sub_problem: SubProblem,
    transcript: List[DebateContribution],
    round: int,
    max_tokens: int = 4000
) -> str:
    """
    Manage context size for expert prompts
    """
    if round <= 10:
        # Early debate: show full transcript
        return format_full_transcript(transcript)
    else:
        # Late debate: summarize early rounds, show recent detail
        early_rounds = transcript[:round-5]  # First N-5 rounds
        recent_rounds = transcript[-(5*len(experts)):]  # Last 5 rounds

        summary = summarize_rounds(early_rounds)  # Use LLM to summarize
        recent = format_full_transcript(recent_rounds)

        return f"{summary}\n\n=== Recent Discussion ===\n{recent}"
```

**Kill Switch:**

```python
if not cost_tracker.check_budget(max_cost=1.0):
    console.print("[bold red]Cost budget exceeded ($1.00). Stopping.[/bold red]")
    # Force early termination, return partial results
    break
```

---

## 13. Quality Metrics & Logging

### Decision: Structured JSON Logging + Per-Deliberation Metrics

**Metrics to Track:**

```python
class DeliberationMetrics(BaseModel):
    sub_problem_id: str

    # Efficiency
    rounds_used: int
    max_rounds_allowed: int
    time_elapsed_seconds: float
    early_stop_triggered: bool
    early_stop_reason: Optional[str]

    # Quality
    final_consensus_level: float  # 0-1
    average_confidence: float  # 0-1
    problem_drift_score: float  # 0-10
    research_requests: int

    # Participation
    contributions_per_expert: dict  # {expert_name: count}
    moderator_interventions: int
    facilitator_redirects: int

    # Convergence trajectory
    convergence_by_round: List[float]
    novelty_by_round: List[float]
    conflict_by_round: List[float]

    # Outcome
    options_generated: int
    vote_distribution: dict
    recommendation_clarity: Optional[str]  # "clear" | "split" | "unclear"
```

**Logging Strategy:**

```python
import logging
import json

# Structured logger
logger = logging.getLogger("bo1")
handler = logging.FileHandler("bo1_sessions.jsonl")  # JSON Lines format
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

# Log each deliberation
logger.info(json.dumps({
    "timestamp": time.time(),
    "session_id": session.id,
    "sub_problem_id": sub_problem.id,
    "metrics": metrics.dict(),
    "cost": cost_tracker.get_cost()
}))
```

**Target Benchmarks (from PRD):**

- Time: 2-4 minutes per sub-problem ✓
- Cost: $0.05-0.15 per sub-problem ✓
- Consensus: >70% for clear decisions ✓
- Early stop rate: 30-40% (adaptive stopping working) ✓

---

## 14. Prompt Engineering Framework

### Decision: Structured XML-Based Prompts with Examples and Chain-of-Thought

**Critical Success Factor:** Prompt quality is the foundation of persona consistency, debate quality, and convergence. We follow the comprehensive framework in `PROMPT_ENGINEERING_FRAMEWORK.md`.

**Core Principles (from framework):**

1. **Explicit > Implicit**: Clear, specific instructions over vague requests
2. **Show, Don't Tell**: 3-5 concrete examples > 500 words of abstract instructions
3. **Structure Everything**: XML tags for complex prompts with multiple components
4. **Make Thinking Visible**: `<thinking>` tags for reasoning before responses
5. **Chain Complex Workflows**: Break multi-step processes into sequential subtasks

**Implementation Strategy:**

```python
# prompts/templates/persona_contribution.xml
PERSONA_CONTRIBUTION_TEMPLATE = """
<system_role>
You are {persona_name}, {persona_description}.

Your role in this deliberation:
- Provide expertise from your unique perspective: {expertise_areas}
- Challenge assumptions and ask probing questions
- Support claims with reasoning and evidence
- Acknowledge limitations of your perspective
- Build on others' contributions constructively

Behavioral guidelines:
- ALWAYS: {always_behaviors}
- NEVER: {never_behaviors}
- WHEN UNCERTAIN: Explicitly state "I'm uncertain about X" rather than speculating
</system_role>

<deliberation_context>
Problem Statement: {problem_statement}

Participants: {participant_list}

Your objectives in this deliberation:
1. Identify risks and opportunities from your domain
2. Provide frameworks or methodologies relevant to this decision
3. Challenge assumptions that may be overlooked
</deliberation_context>

<communication_protocol>
Format your contributions as:

<thinking>
Your private reasoning process:
- What aspects of the problem relate to your expertise?
- What questions or concerns arise from your perspective?
- What evidence or frameworks support your view?
- What are you uncertain about?
</thinking>

<contribution>
Your public statement to the group (2-4 paragraphs):
- Lead with your key insight or concern
- Provide reasoning and evidence
- Reference others' contributions if building on or challenging them
- End with questions or areas needing further exploration
</contribution>
</communication_protocol>

<examples>
{examples}
</examples>
"""

# Load from framework
from prompts.framework import load_template, load_examples

persona_prompt = ChatPromptTemplate.from_template(
    load_template("persona_contribution.xml")
)
```

**Key Prompt Templates:**

1. **Problem Extraction** (`prompts/templates/problem_extraction.xml`)
   - 7-dimension framework (core, context, stakeholders, constraints, success, risks, unknowns)
   - 3 diverse examples showing vague → structured transformation
   - `<thinking>` section for gap identification

2. **Persona Recommendation** (`prompts/templates/persona_recommendation.xml`)
   - Selection criteria (relevance, diversity, coverage)
   - Database-driven catalog integration
   - Diversity check validation

3. **Persona Contribution** (`prompts/templates/persona_contribution.xml`)
   - Role-specific system prompts from persona metadata
   - Response prefilling: `[{persona.name}]\n\n<thinking>`
   - Chain-of-thought requirement

4. **Facilitator Synthesis** (`prompts/templates/facilitator_synthesis.xml`)
   - Multi-step reasoning (analyze → decide → act)
   - Routing logic (continue/research/moderator/vote/synthesize)

5. **Voting** (`prompts/templates/voting.xml`)
   - Confidence calibration protocol
   - Structured vote format

**Quality Assurance:**

```python
# All prompts include:
# 1. Citation requirements (reduce hallucinations)
# 2. Uncertainty protocols ("I don't know" > speculation)
# 3. XML structure for parsing
# 4. 3-5 examples per template
# 5. <thinking> tags for reasoning

# Prompt versioning
# prompts/templates/persona_contribution_v1.xml
# prompts/templates/persona_contribution_v2_prefilling.xml
# prompts/templates/current/persona_contribution.xml (symlink)
```

**Performance Targets (from framework):**
- 40-60% improvement in consistency through structured prompting ✓
- 30-50% improvement in multi-step task accuracy through chaining ✓
- Significant reduction in hallucinations through citation requirements ✓
- Enhanced persona character maintenance through role prompting ✓

**Example Strategy (2-3 per template):**

Per PROMPT_ENGINEERING_FRAMEWORK.md guidance:
- **2 examples minimum**: Shows pattern, edge cases
- **3 examples optimal**: Diverse problem types, different complexities
- **Quality over quantity**: Well-crafted examples > many mediocre ones

Example structure:
```xml
<examples>
<example>
  <user_input>Vague problem statement</user_input>
  <output>Structured, comprehensive extraction</output>
</example>

<example>
  <user_input>Different domain problem</user_input>
  <output>Shows same framework, different application</output>
</example>

<example> <!-- Optional 3rd for edge case -->
  <user_input>Complex multi-dimensional problem</user_input>
  <output>Demonstrates handling complexity</output>
</example>
</examples>
```

**A/B Testing Infrastructure (v1):**

```python
# prompts/ab_testing.py
import random
from typing import Dict, List
from pydantic import BaseModel

class PromptVariant(BaseModel):
    """A/B test variant"""
    name: str                    # "v1_baseline", "v2_enhanced_examples"
    template_path: str           # Path to template file
    hypothesis: str              # What we're testing
    metrics: List[str]           # ["consistency", "hallucination_rate", "user_satisfaction"]

class ABTest(BaseModel):
    """A/B test configuration"""
    test_id: str
    control: PromptVariant       # Current production variant
    treatment: PromptVariant     # New variant to test
    allocation: float = 0.5      # % traffic to treatment (default 50/50)
    min_sample_size: int = 20    # Minimum samples before analysis

class ABTestManager:
    """Manage prompt A/B tests"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_tests: Dict[str, ABTest] = {}

    def create_test(self, test: ABTest):
        """Start new A/B test"""
        self.active_tests[test.test_id] = test
        self.redis.hset(f"ab_test:{test.test_id}", "config", test.model_dump_json())

    def get_variant(self, test_id: str, session_id: str) -> PromptVariant:
        """Get variant for session (consistent assignment)"""
        test = self.active_tests.get(test_id)
        if not test:
            return None

        # Check if already assigned
        assigned = self.redis.hget(f"ab_test:{test_id}:assignments", session_id)
        if assigned:
            return test.control if assigned == "control" else test.treatment

        # New assignment
        variant = "treatment" if random.random() < test.allocation else "control"
        self.redis.hset(f"ab_test:{test_id}:assignments", session_id, variant)

        return test.control if variant == "control" else test.treatment

    def record_metric(self, test_id: str, session_id: str, metric: str, value: float):
        """Record metric for analysis"""
        variant = self.redis.hget(f"ab_test:{test_id}:assignments", session_id)
        self.redis.zadd(
            f"ab_test:{test_id}:metrics:{variant}:{metric}",
            {session_id: value}
        )

    def analyze_test(self, test_id: str) -> dict:
        """Analyze A/B test results"""
        from scipy import stats

        test = self.active_tests[test_id]
        results = {}

        for metric in test.metrics:
            control_scores = self.redis.zrange(
                f"ab_test:{test_id}:metrics:control:{metric}",
                0, -1, withscores=True
            )
            treatment_scores = self.redis.zrange(
                f"ab_test:{test_id}:metrics:treatment:{metric}",
                0, -1, withscores=True
            )

            if len(control_scores) < test.min_sample_size or \
               len(treatment_scores) < test.min_sample_size:
                results[metric] = {"status": "insufficient_data"}
                continue

            control_values = [score for _, score in control_scores]
            treatment_values = [score for _, score in treatment_scores]

            t_stat, p_value = stats.ttest_ind(control_values, treatment_values)

            results[metric] = {
                "control_mean": sum(control_values) / len(control_values),
                "treatment_mean": sum(treatment_values) / len(treatment_values),
                "p_value": p_value,
                "significant": p_value < 0.05,
                "lift": ((sum(treatment_values) / len(treatment_values)) /
                         (sum(control_values) / len(control_values)) - 1) * 100
            }

        return results

# Usage
ab_manager = ABTestManager(redis_client)

# Create test
ab_manager.create_test(ABTest(
    test_id="persona_contribution_v2",
    control=PromptVariant(
        name="v1_baseline",
        template_path="prompts/templates/persona_contribution_v1.xml",
        hypothesis="Baseline persona contribution quality",
        metrics=["consistency", "hallucination_rate", "contribution_quality"]
    ),
    treatment=PromptVariant(
        name="v2_enhanced_examples",
        template_path="prompts/templates/persona_contribution_v2.xml",
        hypothesis="Adding 3rd example improves consistency",
        metrics=["consistency", "hallucination_rate", "contribution_quality"]
    ),
    allocation=0.5,
    min_sample_size=20
))

# During deliberation
variant = ab_manager.get_variant("persona_contribution_v2", session_id)
# Use variant.template_path for this session

# After session
ab_manager.record_metric("persona_contribution_v2", session_id, "consistency", 0.85)

# Analyze after sufficient samples
results = ab_manager.analyze_test("persona_contribution_v2")
```

**A/B Testing Workflow:**

1. **Week 1-2**: Run baseline (collect metrics)
2. **Week 3**: Create variant with hypothesis (e.g., "3rd example improves consistency")
3. **Week 4-5**: Run A/B test (50/50 split, 20+ samples per variant)
4. **Week 6**: Analyze results, promote winner
5. **Repeat**: Continuous iteration

**Metrics to Track:**
- **Consistency**: Do personas maintain character? (0-1 scale)
- **Hallucination rate**: % of claims without citation (lower better)
- **Contribution quality**: User rating 1-5
- **Problem drift**: Relevance to sub-problem (0-10 scale)
- **Synthesis clarity**: Final recommendation quality (1-5)

**Why A/B Testing in v1:**
- ✅ **Critical for quality**: Prompts are foundation, must iterate
- ✅ **Low overhead**: Redis tracking, simple implementation
- ✅ **Fast feedback**: 2-3 week test cycles
- ✅ **Data-driven**: Move from guessing to measuring
- ✅ **Foundation for v2**: Establish testing culture early

---

## 15. Development Phases

### Phase 1: Core Functionality (Weeks 1-3)

**Week 1: Foundation**

- [ ] Project setup (Python, dependencies, structure)
- [ ] Pydantic state models (Problem, SubProblem, PersonaProfile, etc.)
- [ ] Claude API integration (BaseAgent class)
- [ ] Basic console UI (Rich setup, prompts)

**Week 2: Core Orchestration**

- [ ] Problem decomposition (LLM-based)
- [ ] Expert persona pool + selection algorithm
- [ ] Deliberation engine (round management)
- [ ] Facilitator agent (summarization, option formulation)

**Week 3: Voting & Synthesis**

- [ ] Voting mechanism (parallel expert votes)
- [ ] Confidence calibration
- [ ] Vote aggregation (simple majority)
- [ ] Final synthesis + recommendation generation

**Milestone**: End-to-end session works (simple problem → recommendation)

---

### Phase 2: Quality & Convergence (Weeks 4-5)

**Week 4: Convergence Mechanics**

- [ ] Embedding-based similarity calculations
- [ ] Convergence monitoring (semantic similarity, novelty, conflict)
- [ ] Early stopping logic
- [ ] Problem drift detection

**Week 5: Interventions**

- [ ] Moderator personas (Contrarian, Skeptic, Optimist)
- [ ] Intervention trigger logic
- [ ] Facilitator redirects
- [ ] Research request detection + Researcher agent

**Milestone**: Adaptive stopping + quality controls working

---

### Phase 3: Polish & Testing (Weeks 6-7)

**Week 6: UI & UX**

- [ ] Rich console formatting (panels, trees, colors)
- [ ] Progress indicators
- [ ] User checkpoints (continue/skip/intervene)
- [ ] Markdown export

**Week 7: Testing & Optimization**

- [ ] Test with 10+ diverse problems (solopreneur scenarios from PRD)
- [ ] Metrics validation (time, cost, consensus)
- [ ] Cost optimization (context management, parallel execution)
- [ ] Bug fixes + edge case handling

**Milestone**: v1 ready for personal use

---

## 15. Open Questions & Risks

### Open Questions

1. **Persona pool size**: 12 or 15 or 20 personas? (More = better coverage, harder to maintain)
2. **Embedding model**: all-MiniLM-L6-v2 (fast) vs. larger model (more accurate)?
3. **User intervention mechanism**: Checkpoints only, or allow real-time intervention?
4. **Markdown export format**: Full transcript vs. executive summary vs. both?

### Risks & Mitigations

| Risk                                       | Mitigation                                                    |
| ------------------------------------------ | ------------------------------------------------------------- |
| **LLM cost overrun**                       | Token budgeting, kill switches, early stopping                |
| **Poor decomposition quality**             | User review/edit step, fallback to single sub-problem         |
| **Debate goes off-topic (drift)**          | Drift detection, facilitator redirects, hard round caps       |
| **Experts converge too fast (groupthink)** | Contrarian moderator, diversity enforcement                   |
| **Debate never converges (deadlock)**      | Hard round cap (15), optimist moderator, force vote           |
| **Synthesis is vague/unclear**             | Structured prompts, example-driven, user can request revision |

---

## 16. Success Criteria (v1 Release)

### Functional Requirements

- ✓ Successfully decomposes 90% of test problems (10+ diverse scenarios)
- ✓ Generates actionable recommendations with clear rationale
- ✓ Completes typical session in 5-15 minutes
- ✓ Surfaces trade-offs in 100% of recommendations
- ✓ Adaptive stopping works (30-40% early stop rate)
- ✓ User intervention mechanism works at checkpoints
- ✓ Handles edge cases gracefully (too simple/complex, drift, deadlock)

### Quality Benchmarks

- ✓ Consensus level: >70% for clear decisions
- ✓ Average confidence: >0.7 for final votes
- ✓ Problem drift: <10% of deliberations
- ✓ Cost: <$1 per typical session (3-5 sub-problems)
- ✓ Time: 2-4 minutes per sub-problem average

### User Experience

- ✓ Clear, readable console UI (Rich formatting)
- ✓ User can intervene at checkpoints
- ✓ Export transcript (JSON + Markdown)
- ✓ Recommendations are advisory, not directive

---

## 17. Future Enhancements (v2+)

### Phase 2 (Post-v1)

- Web interface (Streamlit or custom React app)
- Persistent sessions (pause/resume with SQLite)
- Export to PDF, Notion, Google Docs
- Verbosity levels (concise, standard, detailed)
- Real-time streaming UI (show contributions as they complete)

### Phase 3

- Custom expert personas (user-defined)
- External research integration (web search, APIs)
- Multi-provider support (OpenAI, Gemini, local models)
- Expert learning from feedback
- Problem templates for common scenarios

### Phase 4

- Team collaboration (shared sessions)
- Expert marketplace (community personas)
- Integration with task managers (Todoist, Linear)
- Mobile app

---

## 18. Updated Technology Summary

**Final Stack (November 2025):**

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | Python 3.12+ | Latest stable, performance improvements, best AI ecosystem |
| **Package Manager** | uv | 10-100x faster than pip, reproducible builds |
| **LLM** | Claude Haiku 4.5 + Sonnet 4.5 | Superior prompt adherence, structured output quality |
| **Orchestration** | LangChain (library mode) | Prompt management, caching, parallel execution |
| **State** | Redis | Fast in-memory, TTL support, LangChain integration |
| **Embeddings** | Voyage AI (voyage-3) | State-of-the-art similarity, API-based, low cost |
| **Console UI** | Rich | Beautiful formatting, progress bars, markdown |
| **Prompts** | XML-based framework | Structured, examples, chain-of-thought (PROMPT_ENGINEERING_FRAMEWORK.md) |
| **Personas** | 35-persona pool | Pre-defined, optimized prompts, diverse coverage |

---

## 19. Recommendation

**Proceed with this updated implementation proposal for bo1 v1.**

**Key Strengths:**

- **Modern stack**: Python 3.12, uv, Claude 4.5, Voyage AI
- **Proven tools**: LangChain for orchestration, Redis for state
- **Quality-first**: Comprehensive prompt engineering framework
- **Research-backed**: Convergence mechanics, persona diversity
- **Cost-efficient**: <$1 per session target maintained
- **Scalable foundation**: Redis + LangChain enable v2 features

**Critical Success Factors:**

1. **Prompt Engineering**: Follow PROMPT_ENGINEERING_FRAMEWORK.md rigorously
2. **35 Personas**: Carefully craft diverse, well-balanced persona pool
3. **XML Structure**: All prompts use structured tags + examples
4. **Chain-of-Thought**: `<thinking>` tags in every contribution
5. **Voyage AI**: Leverage state-of-the-art embeddings for convergence

**Implementation Decisions Summary:**

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Deployment** | Docker Compose (Redis + bo1 app) | Reproducible, easy onboarding, isolated services |
| **Personas** | Use existing 35 from `old_docs/personas.json` | Pre-built system prompts, safety guidelines, trait diversity |
| **Examples** | 2-3 per template | Optimal for showing pattern + diversity without bloat |
| **A/B Testing** | Include in v1 with Redis tracking | Critical for prompt quality, low overhead, fast iteration |

**Next Steps:**

1. **Week 1**: Set up development environment
   - Install Docker Desktop
   - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Clone repo, run: `docker-compose up`
   - Get API keys: Anthropic, Voyage AI (add to `.env`)

2. **Week 2-3**: Implement Phase 1 (Foundation)
   - Pydantic models + Redis state management
   - LangChain integration (Haiku + Sonnet)
   - Prompt templates (XML-based, with examples)
   - 35-persona pool with metadata

3. **Week 4-7**: Phases 2-3 (Quality + Polish)
   - Convergence mechanics (Voyage AI embeddings)
   - Console UI (Rich)
   - Testing with solopreneur scenarios

**Estimated Timeline**: 7 weeks to production-ready v1

**What's NOT in v1 (Deferred to v2):**

1. **FastAPI**: No web interface in v1 (console-only per PRD section 10)
2. **LangGraph**: Linear orchestration sufficient for v1, add when we need stateful graphs + streaming
3. **Postgres**: Redis sufficient for v1, add Postgres in v2 for long-term storage
4. **Web UI**: Console with Rich library only
5. **Auth**: No authentication in v1 (single user console app)
6. **Monitoring**: No Prometheus/Grafana in v1
7. **Vector Storage**: No pgvector in v1 (Voyage AI embeddings ephemeral)

**v1 to v2 Migration Path:**

```
v1 (Console)                           v2 (Web Interface)
├─ LangChain (chains)            →     ├─ LangGraph (state machines, streaming)
├─ Redis (state)                 →     ├─ Redis (hot state) + Postgres (cold storage)
├─ Rich (console)                →     ├─ Svelte 5 + SvelteKit (frontend)
├─ No auth                       →     ├─ Supabase Auth (Google/GitHub/LinkedIn)
├─ No API                        →     ├─ FastAPI (backend API)
├─ Voyage AI (ephemeral)         →     ├─ pgvector (persistent embeddings)
├─ No monitoring                 →     ├─ Prometheus + Grafana (observability)
└─ Sequential flow               →     └─ Traefik (reverse proxy, load balancing)
```

**v2 Technology Stack (Web Interface):**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Svelte 5 + SvelteKit | Modern reactive UI, SSR, file-based routing |
| **Backend API** | FastAPI | High-performance Python API, async support |
| **Auth** | Supabase Auth | OAuth (Google, GitHub, LinkedIn), session management |
| **Database** | PostgreSQL | Long-term storage, user data, session history |
| **Vector DB** | pgvector (Postgres extension) | Store/search embeddings for similarity |
| **Connection Pool** | PgBouncer | Postgres connection pooling (reduce overhead) |
| **State** | Redis | Hot state, real-time deliberation, LLM cache |
| **Orchestration** | LangGraph | Stateful workflows, streaming, pause/resume |
| **Reverse Proxy** | Traefik | Load balancing, SSL termination, routing |
| **Metrics** | Prometheus | Time-series metrics, alerts |
| **Dashboards** | Grafana | Visualization, monitoring, alerting |
| **Analytics** | PostHog (optional) | Product analytics, feature flags |
| **Error Tracking** | Sentry (optional) | Error monitoring, performance tracking |

**v2 Docker Compose (Full Stack):**

```yaml
# docker-compose.v2.yml
version: '3.8'

services:
  # Database tier
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: bo1
      POSTGRES_USER: bo1
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bo1"]
      interval: 5s

  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DATABASE_URL: postgres://bo1:${POSTGRES_PASSWORD}@postgres:5432/bo1
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
    depends_on:
      postgres:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  # Backend tier
  fastapi:
    build: ./backend
    environment:
      DATABASE_URL: postgres://bo1:${POSTGRES_PASSWORD}@pgbouncer:6432/bo1
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      VOYAGE_API_KEY: ${VOYAGE_API_KEY}
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_KEY: ${SUPABASE_KEY}
    depends_on:
      - pgbouncer
      - redis

  # Frontend tier
  sveltekit:
    build: ./frontend
    environment:
      PUBLIC_SUPABASE_URL: ${SUPABASE_URL}
      PUBLIC_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
      BACKEND_API_URL: http://fastapi:8000

  # Reverse proxy
  traefik:
    image: traefik:v3.0
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik.yml:/traefik.yml
      - ./acme.json:/acme.json
    labels:
      - "traefik.enable=true"

  # Monitoring tier
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

volumes:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

**Why This Stack for v2:**

- **Svelte 5**: Fastest framework, smallest bundle size, runes for reactivity
- **SvelteKit**: SSR, SEO-friendly, file-based routing, server actions
- **Supabase**: Managed auth, row-level security, real-time subscriptions
- **pgvector**: Store embeddings in Postgres (simplifies architecture vs separate vector DB)
- **PgBouncer**: Essential for connection pooling with many concurrent users
- **Traefik**: Modern reverse proxy, auto SSL, great for microservices
- **Prometheus + Grafana**: Industry standard monitoring stack

**Open Questions - RESOLVED:**

1. ✅ **Docker Deployment**: All services containerized (Redis, bo1 app)
2. ✅ **Persona Pool**: Use existing 35 personas from `old_docs/personas.json`
3. ✅ **Example Library**: 2-3 high-quality examples per prompt template
4. ✅ **A/B Testing**: Include in v1 for prompt iteration

---

**Document Version**: 2.0 (Updated for November 2025)
**Status**: Ready for Implementation
**Author**: Implementation Team
**Date**: 2025-11-11
**Changes from v1.0**: Python 3.12+, uv, Redis, LangChain, Voyage AI, 35 personas, prompt framework integration
