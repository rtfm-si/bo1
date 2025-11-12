"""Demo script - Full Days 8-11 implementation."""

import asyncio

from bo1.agents.decomposer import DecomposerAgent
from bo1.agents.selector import PersonaSelectorAgent
from bo1.models.persona import PersonaProfile
from bo1.models.state import DeliberationPhase, DeliberationState
from bo1.orchestration.deliberation import DeliberationEngine
from bo1.ui.console import Console


async def main() -> None:
    """Run full Days 8-11 demo: decomposition → selection → initial round."""
    console = Console()

    # Step 1: Problem Intake & Decomposition
    console.print_header("Board of One - Current Demo (Days 8-11)")
    console.print("\n[cyan]Step 1:[/cyan] Problem Decomposition\n")

    decomposer = DecomposerAgent()
    problem_input = "Should I invest $50K in SEO or paid ads for my SaaS startup?"
    console.print(f"[bold]Problem:[/bold] {problem_input}\n")

    console.print("[dim]Decomposing problem...[/dim]\n")
    decomposition, decomp_usage, decomp_cost = await decomposer.decompose_problem(
        problem_description=problem_input,
        context="Solo founder, SaaS product, $100K ARR, need to grow",
        constraints=["Budget: $50K", "Timeline: 6 months"],
    )

    console.print_decomposition(decomposition)
    console.print_llm_cost(
        phase="Decomposition", token_usage=decomp_usage, cost=decomp_cost, model_name="sonnet-4.5"
    )

    is_valid, errors = decomposer.validate_decomposition(decomposition)
    if not is_valid:
        console.print_error(f"Invalid decomposition: {errors}")
        return

    problem = decomposer.create_problem_from_decomposition(
        title="Growth Investment Decision",
        problem_description=problem_input,
        context="Solo founder, SaaS product, $100K ARR",
        decomposition=decomposition,
    )

    # Step 2: Persona Selection
    console.print("\n[cyan]Step 2:[/cyan] Persona Selection\n")

    selector = PersonaSelectorAgent()
    first_sp = problem.sub_problems[0]
    console.print(f"[bold]Selecting personas for:[/bold] {first_sp.goal}\n")

    console.print("[dim]Recommending personas...[/dim]\n")
    recommendation, selector_usage, selector_cost = await selector.recommend_personas(
        sub_problem=first_sp, problem_context=problem.context
    )

    console.print(f"\n[bold]Analysis:[/bold] {recommendation['analysis']}\n")
    console.print_llm_cost(
        phase="Persona Selection",
        token_usage=selector_usage,
        cost=selector_cost,
        model_name="sonnet-4.5",
    )

    persona_codes = [p["code"] for p in recommendation["recommended_personas"]]
    personas_data = selector.get_personas_by_codes(persona_codes)
    persona_profiles = [PersonaProfile(**p) for p in personas_data]

    console.print_personas(persona_profiles, title="Selected Expert Panel")

    # Step 3: Initial Round (Parallel Contributions)
    console.print("\n[cyan]Step 3:[/cyan] Initial Round (Parallel Contributions)\n")

    state = DeliberationState(
        session_id="demo-session",
        problem=problem,
        current_sub_problem=first_sp,
        selected_personas=persona_profiles,
        phase=DeliberationPhase.SELECTION,
    )

    engine = DeliberationEngine(state)
    console.print(
        f"[dim]Running parallel contributions from {len(persona_profiles)} personas...[/dim]\n"
    )

    contributions = await engine.run_initial_round()

    # Display contributions
    for contrib in contributions:
        console.print_contribution(
            persona_name=contrib.persona_name,
            persona_code=contrib.persona_code,
            content=f"{contrib.thinking or ''}\n\n{contrib.content}",
            round_number=contrib.round_number,
            tokens_used=contrib.token_count or 0,
            cost=contrib.cost or 0.0,
        )

    # Display summary metrics
    console.print("\n[cyan]Summary Metrics[/cyan]\n")

    # Calculate total costs including decomposition and selection
    total_cost = decomp_cost + selector_cost + engine.get_total_cost()
    total_tokens = (
        decomp_usage.total_tokens + selector_usage.total_tokens + engine.get_total_tokens()
    )

    metrics = {
        "total_cost": total_cost,
        "decomposition_cost": decomp_cost,
        "selection_cost": selector_cost,
        "deliberation_cost": engine.get_total_cost(),
        "total_tokens": total_tokens,
        "contributions": len(contributions),
        "personas": len(persona_profiles),
    }
    console.print_metrics(metrics)

    console.print_success("\n✨ Demo complete! Days 8-11 functionality verified.\n")
    console.print(
        "[dim]Note: Multi-round deliberation, voting, and synthesis (Days 12-14) are not yet implemented.[/dim]\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
