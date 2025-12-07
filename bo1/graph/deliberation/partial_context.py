"""Partial context provider for speculative parallel sub-problem execution.

This module enables dependent sub-problems to start early by sharing
partial context from in-progress deliberations.

Key Features:
- Thread-safe context sharing between concurrent sub-problems
- Progressive context updates as rounds complete
- Early start support (dependent SPs can begin with partial data)

Usage:
    provider = PartialContextProvider()

    # SP0 updates context after each round
    provider.update_round_context(sp_index=0, round_num=2, round_summary="...")

    # SP1 can get partial context before SP0 completes
    context = provider.get_partial_context(
        sp_index=1,
        dependency_indices=[0]
    )
"""

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SubProblemProgress:
    """Tracks progress and partial results of an in-progress sub-problem."""

    sp_index: int
    sp_id: str
    goal: str

    # Round-by-round progress
    completed_rounds: int = 0
    max_rounds: int = 6
    round_summaries: list[str] = field(default_factory=list)

    # Key insights extracted from early rounds
    early_insights: list[str] = field(default_factory=list)

    # Expert panel for context
    expert_panel: list[str] = field(default_factory=list)

    # Full result (set when complete)
    is_complete: bool = False
    final_synthesis: str | None = None
    final_recommendation: str | None = None

    def get_progress_percentage(self) -> float:
        """Return progress as percentage (0.0 - 1.0)."""
        if self.is_complete:
            return 1.0
        return self.completed_rounds / self.max_rounds if self.max_rounds > 0 else 0.0


@dataclass
class PartialContext:
    """Partial context available from dependencies."""

    dependency_progress: dict[int, SubProblemProgress]  # sp_index -> progress
    available_context: str  # Formatted context string for prompts
    all_dependencies_ready: bool  # True if all deps have >= early_start_threshold rounds
    all_dependencies_complete: bool  # True if all deps are fully complete


class PartialContextProvider:
    """Provides thread-safe partial context sharing between sub-problems.

    This enables speculative parallel execution where dependent sub-problems
    can start early (when dependencies reach round 2) instead of waiting
    for full completion.

    Thread Safety:
    - Uses asyncio.Lock for concurrent access
    - Safe for parallel sub-problem execution

    Example:
        >>> provider = PartialContextProvider(early_start_threshold=2)
        >>>
        >>> # SP0 completes round 2
        >>> await provider.update_round_context(
        ...     sp_index=0, sp_id="sp_001", goal="Market analysis",
        ...     round_num=2, round_summary="Key insight: B2C market is 10x larger"
        ... )
        >>>
        >>> # SP1 (depends on SP0) can now start with partial context
        >>> context = await provider.get_partial_context(sp_index=1, dependency_indices=[0])
        >>> context.all_dependencies_ready  # True (SP0 has >= 2 rounds)
    """

    def __init__(self, early_start_threshold: int = 2) -> None:
        """Initialize the context provider.

        Args:
            early_start_threshold: Number of completed rounds required before
                dependent sub-problems can start. Default: 2 (after exploration phase)
        """
        self._lock = asyncio.Lock()
        self._progress: dict[int, SubProblemProgress] = {}
        self._early_start_threshold = early_start_threshold
        self._ready_events: dict[int, asyncio.Event] = {}
        self._complete_events: dict[int, asyncio.Event] = {}

    async def register_subproblem(
        self,
        sp_index: int,
        sp_id: str,
        goal: str,
        max_rounds: int = 6,
        expert_panel: list[str] | None = None,
    ) -> None:
        """Register a sub-problem before it starts executing.

        Args:
            sp_index: Index of the sub-problem (0-based)
            sp_id: Unique identifier for the sub-problem
            goal: Goal/description of the sub-problem
            max_rounds: Maximum number of deliberation rounds
            expert_panel: List of expert codes on the panel
        """
        async with self._lock:
            self._progress[sp_index] = SubProblemProgress(
                sp_index=sp_index,
                sp_id=sp_id,
                goal=goal,
                max_rounds=max_rounds,
                expert_panel=expert_panel or [],
            )
            self._ready_events[sp_index] = asyncio.Event()
            self._complete_events[sp_index] = asyncio.Event()

            logger.debug(f"PartialContextProvider: Registered SP {sp_index} ({sp_id})")

    async def update_round_context(
        self,
        sp_index: int,
        round_num: int,
        round_summary: str,
        early_insights: list[str] | None = None,
    ) -> None:
        """Update context after a round completes.

        This should be called after each deliberation round to share
        progress with dependent sub-problems.

        Args:
            sp_index: Index of the sub-problem
            round_num: The round number that just completed (1-based)
            round_summary: Summary of the round's deliberation
            early_insights: Optional list of key insights from this round
        """
        async with self._lock:
            if sp_index not in self._progress:
                logger.warning(f"PartialContextProvider: SP {sp_index} not registered")
                return

            progress = self._progress[sp_index]
            progress.completed_rounds = round_num
            progress.round_summaries.append(round_summary)

            if early_insights:
                progress.early_insights.extend(early_insights)

            logger.debug(
                f"PartialContextProvider: SP {sp_index} completed round {round_num}/"
                f"{progress.max_rounds}"
            )

            # Signal if ready threshold reached
            if round_num >= self._early_start_threshold:
                self._ready_events[sp_index].set()
                logger.info(
                    f"PartialContextProvider: SP {sp_index} ready for dependent start "
                    f"(round {round_num} >= threshold {self._early_start_threshold})"
                )

    async def mark_complete(
        self,
        sp_index: int,
        final_synthesis: str,
        final_recommendation: str | None = None,
    ) -> None:
        """Mark a sub-problem as fully complete.

        Args:
            sp_index: Index of the sub-problem
            final_synthesis: Full synthesis text
            final_recommendation: Extracted key recommendation
        """
        async with self._lock:
            if sp_index not in self._progress:
                logger.warning(f"PartialContextProvider: SP {sp_index} not registered")
                return

            progress = self._progress[sp_index]
            progress.is_complete = True
            progress.final_synthesis = final_synthesis
            progress.final_recommendation = final_recommendation

            # Signal completion
            self._ready_events[sp_index].set()  # Also set ready if not already
            self._complete_events[sp_index].set()

            logger.info(f"PartialContextProvider: SP {sp_index} marked complete")

    async def wait_for_ready(
        self,
        dependency_indices: list[int],
        timeout: float | None = None,
    ) -> bool:
        """Wait until all dependencies reach early start threshold.

        Args:
            dependency_indices: List of dependency sub-problem indices
            timeout: Optional timeout in seconds

        Returns:
            True if all dependencies are ready, False if timeout
        """
        if not dependency_indices:
            return True

        events = [
            self._ready_events.get(idx) for idx in dependency_indices if idx in self._ready_events
        ]

        if not events:
            logger.warning(f"PartialContextProvider: No events for deps {dependency_indices}")
            return False

        try:
            # Wait for all events with optional timeout
            await asyncio.wait_for(
                asyncio.gather(*[e.wait() for e in events if e]),
                timeout=timeout,
            )
            return True
        except TimeoutError:
            logger.warning(f"PartialContextProvider: Timeout waiting for deps {dependency_indices}")
            return False

    async def wait_for_complete(
        self,
        dependency_indices: list[int],
        timeout: float | None = None,
    ) -> bool:
        """Wait until all dependencies are fully complete.

        Args:
            dependency_indices: List of dependency sub-problem indices
            timeout: Optional timeout in seconds

        Returns:
            True if all dependencies complete, False if timeout
        """
        if not dependency_indices:
            return True

        events = [
            self._complete_events.get(idx)
            for idx in dependency_indices
            if idx in self._complete_events
        ]

        if not events:
            return False

        try:
            await asyncio.wait_for(
                asyncio.gather(*[e.wait() for e in events if e]),
                timeout=timeout,
            )
            return True
        except TimeoutError:
            return False

    async def get_partial_context(
        self,
        sp_index: int,
        dependency_indices: list[int],
    ) -> PartialContext:
        """Get partial context from dependencies for a sub-problem.

        This returns whatever context is currently available from
        the dependency sub-problems, whether complete or in-progress.

        Args:
            sp_index: Index of the requesting sub-problem
            dependency_indices: List of dependency sub-problem indices

        Returns:
            PartialContext with available dependency information
        """
        async with self._lock:
            dep_progress: dict[int, SubProblemProgress] = {}
            all_ready = True
            all_complete = True

            for dep_idx in dependency_indices:
                if dep_idx in self._progress:
                    dep_progress[dep_idx] = self._progress[dep_idx]
                    if self._progress[dep_idx].completed_rounds < self._early_start_threshold:
                        all_ready = False
                    if not self._progress[dep_idx].is_complete:
                        all_complete = False
                else:
                    all_ready = False
                    all_complete = False

            # Build formatted context string
            context_str = self._format_partial_context(dep_progress)

            return PartialContext(
                dependency_progress=dep_progress,
                available_context=context_str,
                all_dependencies_ready=all_ready,
                all_dependencies_complete=all_complete,
            )

    def _format_partial_context(self, dep_progress: dict[int, SubProblemProgress]) -> str:
        """Format dependency progress into a context string for prompts.

        Args:
            dep_progress: Dictionary of dependency progress objects

        Returns:
            Formatted context string
        """
        if not dep_progress:
            return ""

        parts = ["<dependency_context>"]
        parts.append("Context from related focus areas (may be in-progress):\n")

        for _sp_idx, progress in sorted(dep_progress.items()):
            status = (
                "Complete"
                if progress.is_complete
                else f"In Progress ({progress.completed_rounds}/{progress.max_rounds} rounds)"
            )
            parts.append(f"\n**{progress.goal}** [{status}]")

            if progress.is_complete and progress.final_recommendation:
                parts.append(f"Key Conclusion: {progress.final_recommendation}")
            elif progress.early_insights:
                parts.append("Emerging Insights:")
                for insight in progress.early_insights[:3]:  # Limit to 3
                    parts.append(f"  - {insight}")
            elif progress.round_summaries:
                # Use latest round summary as fallback
                parts.append(f"Latest Discussion: {progress.round_summaries[-1][:300]}...")

            if progress.expert_panel:
                parts.append(f"Expert Panel: {', '.join(progress.expert_panel)}")
            parts.append("")

        parts.append("</dependency_context>")
        return "\n".join(parts)

    async def get_all_progress(self) -> dict[int, SubProblemProgress]:
        """Get progress for all registered sub-problems.

        Returns:
            Dictionary of sp_index -> SubProblemProgress
        """
        async with self._lock:
            return dict(self._progress)

    def get_early_start_threshold(self) -> int:
        """Get the configured early start threshold."""
        return self._early_start_threshold
