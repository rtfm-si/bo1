#!/usr/bin/env python3
"""Board of One - Complete Demo (Days 1-14).

Demonstrates the full end-to-end pipeline:
1. Problem decomposition with sub-problems
2. Information gap detection (INTERNAL vs EXTERNAL)
3. Context collection (business, internal answers, research)
4. Persona selection based on problem domain
5. Initial round of expert contributions (parallel)
6. Multi-round deliberation with facilitator
7. Moderator interventions
8. Convergence detection
9. Final synthesis (placeholder - Day 15)

Run: make demo
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.researcher import ResearcherAgent
from bo1.agents.selector import PersonaSelectorAgent
from bo1.llm.broker import PromptBroker
from bo1.llm.response import DeliberationMetrics
from bo1.models.state import DeliberationState
from bo1.orchestration.deliberation import DeliberationEngine
from bo1.ui.console import Console

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configure logging from environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
debug_mode = os.getenv("DEBUG", "false").lower() == "true"
# VERBOSE_LIBS=true will show third-party library debug logs (anthropic, httpx, etc.)
verbose_libs = os.getenv("VERBOSE_LIBS", "false").lower() == "true"

# Custom formatter for cleaner output
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
if log_level == "INFO":
    # Simpler format for INFO level (less noise)
    log_format = "%(levelname)s - %(message)s"

logging.basicConfig(
    level=getattr(logging, log_level),
    format=log_format,
)

# Always suppress noisy third-party loggers unless VERBOSE_LIBS=true
# This applies even when DEBUG=true to keep output readable
if not verbose_libs:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("anthropic._base_client").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def run_complete_demo() -> None:
    """Run the complete Board of One deliberation pipeline (Days 1-14)."""
    console = Console()

    # Header
    console.print("\n" + "=" * 70)
    console.print_header("Board of One - Complete Pipeline Demo")
    console.print("=" * 70 + "\n")

    # Initialize all agents
    broker = PromptBroker()
    decomposer = DecomposerAgent(broker=broker)
    selector = PersonaSelectorAgent(broker=broker)
    researcher = ResearcherAgent()

    # Track all LLM calls for metrics
    all_metrics = DeliberationMetrics(session_id="demo-session", responses=[])

    # ==================== STEP 1: Problem Decomposition ====================
    console.print("\n[bold cyan]═══ Step 1: Problem Decomposition ═══[/bold cyan]\n")

    problem_description = (
        "I'm a solo founder of a B2B SaaS product with $100K ARR and 50 customers. "
        "I have $50K to invest in growth over the next 6 months. "
        "Should I focus on SEO content marketing or paid advertising (Google/LinkedIn)?"
    )

    console.print(f"[dim]Problem: {problem_description}[/dim]\n")

    decomposition_response = await decomposer.decompose_problem(
        problem_description=problem_description,
        context="Solo founder, B2B SaaS, $100K ARR, 50 customers, $50K budget, 6 months",
        constraints=["Budget: $50K", "Timeline: 6 months"],
    )
    all_metrics.add_response(decomposition_response)

    decomposition = json.loads(decomposition_response.content)
    console.print(
        f"[green]✓ Decomposed into {len(decomposition['sub_problems'])} sub-problems[/green]\n"
    )

    for i, sp in enumerate(decomposition["sub_problems"], 1):
        console.print(f"  {i}. {sp['goal']}")
        console.print(f"     [dim]Complexity: {sp['complexity_score']}/10[/dim]")

    # ==================== STEP 2: Information Gap Detection ====================
    console.print("\n[bold cyan]═══ Step 2: Information Gap Detection ═══[/bold cyan]\n")

    # Skip business context collection for demo (non-interactive)
    business_context = None

    gaps_response = await decomposer.identify_information_gaps(
        problem_description=problem_description,
        sub_problems=decomposition["sub_problems"],
        business_context=business_context,
    )
    all_metrics.add_response(gaps_response)

    gaps = json.loads(gaps_response.content)
    internal_gaps = gaps.get("internal_gaps", [])
    external_gaps = gaps.get("external_gaps", [])

    console.print(
        f"[green]✓ Identified {len(internal_gaps)} internal and {len(external_gaps)} external gaps[/green]\n"
    )

    # Show sample gaps
    if internal_gaps:
        console.print("[yellow]Sample internal gap:[/yellow]")
        console.print(f"  Q: {internal_gaps[0]['question']}")
        console.print(f"  [dim]Priority: {internal_gaps[0]['priority']}[/dim]\n")

    if external_gaps:
        console.print("[yellow]Sample external gap:[/yellow]")
        console.print(f"  Q: {external_gaps[0]['question']}")
        console.print(f"  [dim]Priority: {external_gaps[0]['priority']}[/dim]\n")

    # Skip actual collection for automated demo
    console.print("[dim]Skipping context collection for demo (would be interactive)[/dim]\n")
    internal_answers: dict[str, str] = {}

    # Research stub
    if external_gaps:
        research_results = await researcher.research_questions(external_gaps[:3])  # Limit to 3
        console.print(f"[dim]Research stub: {len(research_results)} placeholder results[/dim]\n")
    else:
        research_results = []

    # ==================== STEP 3: Persona Selection ====================
    console.print("\n[bold cyan]═══ Step 3: Persona Selection ═══[/bold cyan]\n")

    # Pick first sub-problem for demo
    sp_dict = decomposition["sub_problems"][0]
    console.print(f"[dim]Focusing on: {sp_dict['goal']}[/dim]\n")

    # Create SubProblem model
    from bo1.models.problem import SubProblem

    sub_problem_obj = SubProblem(
        id=sp_dict["id"],
        goal=sp_dict["goal"],
        context=sp_dict.get("context", ""),
        complexity_score=sp_dict["complexity_score"],
        dependencies=sp_dict.get("dependencies", []),
    )

    selection_response = await selector.recommend_personas(
        sub_problem=sub_problem_obj,
        problem_context=problem_description,
    )
    all_metrics.add_response(selection_response)

    selection = json.loads(selection_response.content)
    persona_recommendations = selection.get("recommended_personas", [])[:5]  # Max 5

    console.print(f"[green]✓ Selected {len(persona_recommendations)} expert personas[/green]\n")
    for rec in persona_recommendations:
        console.print(f"  • {rec['code']} ({rec['name']}): {rec['rationale']}")

    # Load PersonaProfile objects
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    # Extract just the codes from the recommendations
    persona_codes = [rec["code"] for rec in persona_recommendations]
    personas = [
        PersonaProfile(**p)
        for code in persona_codes
        if (p := get_persona_by_code(code)) is not None
    ]

    # ==================== STEP 4: Initial Round ====================
    console.print("\n[bold cyan]═══ Step 4: Initial Expert Contributions ═══[/bold cyan]\n")

    # Create deliberation state
    from bo1.models.problem import Problem

    problem = Problem(
        title="Growth Channel Selection",
        description=problem_description,
        context="Solo founder, B2B SaaS, limited budget",
        sub_problems=[
            SubProblem(
                id=sp["id"],
                goal=sp["goal"],
                context=sp.get("context", ""),
                complexity_score=sp["complexity_score"],
                dependencies=sp.get("dependencies", []),
            )
            for sp in decomposition["sub_problems"]
        ],
    )

    state = DeliberationState(
        session_id="demo-session",
        problem=problem,
        current_sub_problem=problem.sub_problems[0],
        selected_personas=personas,  # Add selected personas
        business_context=business_context,
        internal_context=internal_answers,
        research_context=research_results,
    )

    # Initialize deliberation engine
    engine = DeliberationEngine(state=state)

    console.print("[dim]Running initial round with selected personas...[/dim]\n")

    contributions, llm_responses = await engine.run_initial_round()
    for response in llm_responses:
        all_metrics.add_response(response)

    console.print(f"[green]✓ Collected {len(state.contributions)} initial contributions[/green]\n")

    # Show sample contribution
    if state.contributions:
        sample = state.contributions[0]
        console.print(f"[yellow]Sample from {sample.persona_name}:[/yellow]")
        preview = sample.content[:200] + "..." if len(sample.content) > 200 else sample.content
        console.print(f"[dim]{preview}[/dim]\n")

    # ==================== STEP 5: Multi-Round Deliberation ====================
    console.print("\n[bold cyan]═══ Step 5: Multi-Round Deliberation ═══[/bold cyan]\n")

    console.print(
        f"[dim]Running up to {state.max_rounds} rounds with facilitator orchestration...[/dim]\n"
    )

    # Note: Full multi-round would happen here, but we'll show structure
    console.print("[yellow]Note: Full multi-round deliberation implemented (Days 12-13)[/yellow]")
    console.print("[yellow]Skipping in demo to save API costs - structure ready[/yellow]\n")

    # Features ready:
    # - Facilitator deciding next actions (continue/vote/research/moderator)
    # - Context building with discussion history
    # - Moderator interventions (contrarian/skeptic/optimist)
    # - Adaptive round limits based on complexity
    # - State persistence after each round

    console.print("[dim]Multi-round features:[/dim]")
    console.print("[dim]  • Facilitator orchestration ✓[/dim]")
    console.print("[dim]  • Dynamic context building ✓[/dim]")
    console.print("[dim]  • Moderator interventions ✓[/dim]")
    console.print("[dim]  • Adaptive round limits ✓[/dim]\n")

    # ==================== STEP 6: Voting & Synthesis (Day 15) ====================
    console.print("\n[bold cyan]═══ Step 6: Voting & Synthesis ═══[/bold cyan]\n")

    console.print("[yellow]Coming in Day 15:[/yellow]")
    console.print("[dim]  • Persona voting with reasoning[/dim]")
    console.print("[dim]  • Vote aggregation (majority + confidence-weighted)[/dim]")
    console.print("[dim]  • Final synthesis report[/dim]")
    console.print("[dim]  • Dissenting views captured[/dim]\n")

    # ==================== Final Metrics ====================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]Demo Complete - Performance Metrics[/bold cyan]")
    console.print("=" * 70 + "\n")

    console.print_deliberation_metrics(all_metrics)

    console.print("\n[bold green]✓ Pipeline complete through Day 14![/bold green]")
    console.print("\n[dim]Key accomplishments:[/dim]")
    console.print("[dim]  • Intelligent problem decomposition ✓[/dim]")
    console.print("[dim]  • Information gap detection (internal/external) ✓[/dim]")
    console.print("[dim]  • Context-aware persona selection ✓[/dim]")
    console.print("[dim]  • Parallel expert contributions ✓[/dim]")
    console.print("[dim]  • Multi-round deliberation framework ✓[/dim]")
    console.print("[dim]  • Cost tracking and optimization ✓[/dim]")
    console.print("\n[dim]Next: Day 15 - Voting & Synthesis[/dim]\n")


if __name__ == "__main__":
    asyncio.run(run_complete_demo())
