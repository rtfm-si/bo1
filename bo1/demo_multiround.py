"""Demo: Multi-round deliberation with facilitator orchestration.

This demonstrates Days 12-13 implementation:
- Facilitator deciding next actions
- Multi-round debate with context building
- Moderator interventions
- Adaptive round limits based on complexity
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.selector import PersonaSelectorAgent
from bo1.llm.broker import PromptBroker
from bo1.llm.response import DeliberationMetrics
from bo1.models.state import DeliberationState
from bo1.orchestration.deliberation import DeliberationEngine
from bo1.ui.console import Console

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configure logging (set to WARNING to reduce noise, use INFO for debugging)

log_level = os.getenv("LOG_LEVEL", "WARNING")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("bo1").setLevel(logging.WARNING)  # Suppress all bo1 module logs

logger = logging.getLogger(__name__)


async def run_multiround_demo() -> None:
    """Run a complete multi-round deliberation demo."""
    console = Console()
    broker = PromptBroker()
    metrics = DeliberationMetrics(session_id="multiround-demo")

    # Problem statement
    problem = """Should I invest $50,000 in SEO optimization or paid advertising for my B2B SaaS product?

Context:
- B2B SaaS selling project management software
- Currently $15K MRR with 50 customers
- 12-month runway remaining
- Small team (3 people)
- Limited brand awareness
- Competitors spending heavily on both SEO and ads"""

    console.print_header("Multi-Round Deliberation Demo")
    console.print(f"\n[bold cyan]Problem:[/bold cyan]\n{problem}\n")

    # Step 1: Decompose problem
    console.print("\n[bold blue]Step 1: Decomposing Problem[/bold blue]")
    decomposer = DecomposerAgent(broker=broker)
    decomposition_response = await decomposer.decompose_problem(problem_description=problem)
    metrics.add_response(decomposition_response)

    # Parse sub-problems
    import json

    decomposition_data = json.loads(decomposition_response.content)
    sub_problems = decomposition_data.get("sub_problems", [])

    if not sub_problems:
        console.print("[red]No sub-problems generated. Exiting.[/red]")
        return

    # Display decomposition with nice tables
    console.print_decomposition(decomposition_data)
    console.print_llm_response(decomposition_response)

    # Use first sub-problem for demo
    sp_dict = sub_problems[0]
    console.print(f"\n[bold yellow]→ Using sub-problem 1 for demo:[/bold yellow] {sp_dict['goal']}")

    # Create SubProblem model
    import uuid

    from bo1.models.problem import SubProblem

    sp = SubProblem(
        id=str(uuid.uuid4()),
        goal=sp_dict["goal"],
        context=sp_dict.get("context", ""),
        complexity_score=sp_dict["complexity_score"],
        dependencies=[],
    )

    # Step 2: Select personas
    console.print("\n[bold blue]Step 2: Selecting Expert Personas[/bold blue]")
    selector = PersonaSelectorAgent(broker=broker)
    selection_response = await selector.recommend_personas(sub_problem=sp)
    metrics.add_response(selection_response)

    # Parse selected personas
    selection_data = json.loads(selection_response.content)
    # The selector returns "recommended_personas"
    persona_list = selection_data.get("recommended_personas", [])
    persona_codes = [p["code"] if isinstance(p, dict) else p for p in persona_list]

    if not persona_codes:
        console.print("[red]No personas selected. Exiting.[/red]")
        console.print(f"[dim]Debug - selection data: {selection_data}[/dim]")
        return

    console.print(f"\n[green]✓ Selected {len(persona_codes)} expert personas[/green]")
    console.print_llm_response(selection_response)

    # Step 3: Create deliberation state
    from bo1.models.persona import PersonaProfile

    # sub_problem already created above as 'sp'
    sub_problem = sp

    # Create persona profiles using full persona data
    from bo1.data import load_personas

    personas = []
    catalog = load_personas()  # Use load_personas() not load_personas_catalog()
    for code in persona_codes:
        persona_data = next((p for p in catalog if p["code"] == code), None)
        if persona_data:
            # PersonaProfile expects the full persona dict from catalog
            personas.append(PersonaProfile(**persona_data))

    # Create a minimal Problem object for the state
    from bo1.models.problem import Problem

    problem_obj = Problem(
        title="SEO vs Paid Ads Investment Decision",
        description=problem,
        context="",  # Required field
        constraints=[],
    )

    # Create state
    state = DeliberationState(
        session_id="multiround-demo",
        problem=problem_obj,
        current_sub_problem=sub_problem,  # Set the current sub-problem directly
        selected_personas=personas,
    )

    # Step 4: Run initial round
    console.print("\n[bold blue]Step 4: Initial Round (Parallel Contributions)[/bold blue]")
    engine = DeliberationEngine(state=state)

    initial_contributions, initial_responses = await engine.run_initial_round()

    # Track metrics
    for response in initial_responses:
        metrics.add_response(response)

    console.print(
        f"\n[green]Initial round complete:[/green] {len(initial_contributions)} contributions"
    )

    # Display initial contributions (abbreviated)
    for contrib in initial_contributions:
        console.print(f"\n[cyan]{contrib.persona_name}:[/cyan]")
        # Show first 200 chars of contribution
        preview = contrib.content[:200] + "..." if len(contrib.content) > 200 else contrib.content
        console.print(f"  {preview}")

    # Step 5: Multi-round deliberation
    console.print("\n[bold blue]Step 5: Multi-Round Deliberation[/bold blue]")

    # Calculate max rounds based on complexity
    max_rounds = engine.calculate_max_rounds(sp.complexity_score)
    console.print(f"\n[yellow]Max rounds for this complexity:[/yellow] {max_rounds}")

    current_round = 1
    rounds_to_run = min(5, max_rounds)  # For demo, run up to 5 rounds

    console.print(f"[yellow]Running {rounds_to_run} rounds (demo limit)...[/yellow]\n")

    for round_num in range(1, rounds_to_run + 1):
        console.print(f"\n[bold magenta]--- Round {round_num}/{max_rounds} ---[/bold magenta]")

        # Check if moderator should trigger (every 5 rounds)
        if round_num % 5 == 0 and round_num > 0:
            moderator_type = engine.moderator.should_trigger_moderator(
                round_num, engine.used_moderators
            )
            if moderator_type:
                console.print(f"[yellow]Moderator trigger: {moderator_type}[/yellow]")

        # Run round (facilitator decides next action)
        contributions, responses = await engine.run_round(
            round_number=round_num, max_rounds=max_rounds
        )

        # Track metrics
        for response in responses:
            metrics.add_response(response)

        # Check if voting phase started
        if state.phase.value == "voting":
            console.print("\n[green]Facilitator decided to move to voting phase![/green]")
            break

        # Display contributions
        for contrib in contributions:
            console.print(f"\n[cyan]{contrib.persona_name}:[/cyan]")
            # Show first 300 chars
            preview = (
                contrib.content[:300] + "..." if len(contrib.content) > 300 else contrib.content
            )
            console.print(f"  {preview}")

        current_round = round_num

    # Step 6: Show metrics
    console.print("\n[bold blue]Step 6: Deliberation Metrics[/bold blue]")
    console.print_deliberation_metrics(metrics)

    # Step 7: Show full discussion context
    console.print("\n[bold blue]Step 7: Full Discussion History[/bold blue]")
    discussion = engine.build_discussion_context(include_thinking=False)
    console.print("\n[dim]" + discussion[:1000] + "...[/dim]\n")

    console.print("\n[bold green]Multi-round deliberation demo complete![/bold green]")
    console.print(f"[yellow]Total rounds:[/yellow] {current_round} (out of {max_rounds} max)")
    console.print(f"[yellow]Total contributions:[/yellow] {len(state.contributions)}")
    console.print(f"[yellow]Final phase:[/yellow] {state.phase.value}")


if __name__ == "__main__":
    asyncio.run(run_multiround_demo())
