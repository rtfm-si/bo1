"""Unit tests for router registry."""

import pytest


class TestRouterRegistry:
    """Tests for ROUTER_REGISTRY and helper functions."""

    def test_get_router_returns_callable(self):
        """get_router() returns a callable for valid router names."""
        from bo1.graph.routers import get_router

        router = get_router("route_phase")
        assert callable(router)

    def test_get_router_raises_keyerror(self):
        """get_router() raises KeyError for unknown router names."""
        from bo1.graph.routers import get_router

        with pytest.raises(KeyError) as exc_info:
            get_router("nonexistent_router")

        assert "nonexistent_router" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_list_routers_complete(self):
        """list_routers() returns all expected router names."""
        from bo1.graph.routers import list_routers

        routers = list_routers()

        # Verify all expected routers are present
        expected = [
            "route_phase",
            "route_facilitator_decision",
            "route_convergence_check",
            "route_clarification",
            "route_after_identify_gaps",
            "route_after_synthesis",
            "route_after_next_subproblem",
            "route_subproblem_execution",
            "route_on_resume",
        ]

        for name in expected:
            assert name in routers, f"Missing router: {name}"

    def test_list_routers_sorted(self):
        """list_routers() returns a sorted list."""
        from bo1.graph.routers import list_routers

        routers = list_routers()
        assert routers == sorted(routers)

    def test_backward_compat_imports(self):
        """Backward compatibility: imports from bo1.graph.routers (file) still work."""
        # Import from the file (which re-exports from package)
        from bo1.graph.routers import (
            _get_problem_attr,
            _get_subproblem_attr,
            _validate_state_field,
            get_problem_attr,
            get_router,
            get_subproblem_attr,
            list_routers,
            log_routing_decision,
            route_after_identify_gaps,
            route_after_next_subproblem,
            route_after_synthesis,
            route_clarification,
            route_convergence_check,
            route_facilitator_decision,
            route_on_resume,
            route_phase,
            route_subproblem_execution,
            validate_state_field,
        )

        # All imports should be callable
        assert callable(route_phase)
        assert callable(route_facilitator_decision)
        assert callable(route_convergence_check)
        assert callable(route_clarification)
        assert callable(route_after_identify_gaps)
        assert callable(route_after_synthesis)
        assert callable(route_after_next_subproblem)
        assert callable(route_subproblem_execution)
        assert callable(route_on_resume)

        # Registry functions
        assert callable(get_router)
        assert callable(list_routers)

        # Utility functions
        assert callable(validate_state_field)
        assert callable(get_problem_attr)
        assert callable(get_subproblem_attr)
        assert callable(log_routing_decision)

        # Private aliases for backward compat
        assert callable(_validate_state_field)
        assert callable(_get_problem_attr)
        assert callable(_get_subproblem_attr)

    def test_registry_functions_match_direct_imports(self):
        """Router functions from registry are the same as direct imports."""
        from bo1.graph.routers import get_router
        from bo1.graph.routers.facilitator import route_facilitator_decision
        from bo1.graph.routers.phase import route_phase
        from bo1.graph.routers.synthesis import route_after_synthesis

        assert get_router("route_phase") is route_phase
        assert get_router("route_facilitator_decision") is route_facilitator_decision
        assert get_router("route_after_synthesis") is route_after_synthesis

    def test_domain_module_imports(self):
        """Individual domain modules can be imported directly."""
        from bo1.graph.routers.facilitator import (
            route_after_identify_gaps,
            route_clarification,
            route_convergence_check,
            route_facilitator_decision,
        )
        from bo1.graph.routers.phase import route_phase
        from bo1.graph.routers.synthesis import (
            route_after_next_subproblem,
            route_after_synthesis,
            route_on_resume,
            route_subproblem_execution,
        )

        # All should be callable
        assert callable(route_phase)
        assert callable(route_facilitator_decision)
        assert callable(route_convergence_check)
        assert callable(route_clarification)
        assert callable(route_after_identify_gaps)
        assert callable(route_after_synthesis)
        assert callable(route_after_next_subproblem)
        assert callable(route_subproblem_execution)
        assert callable(route_on_resume)


class TestRouterNoApiImport:
    """Tests verifying router isolation from API layer."""

    def test_route_after_next_subproblem_no_api_import(self):
        """Verify route_after_next_subproblem has no API layer imports.

        ARCH P3: Router should not import from backend.api to enable
        isolated testing without API dependencies.
        """
        import inspect

        from bo1.graph.routers.synthesis import route_after_next_subproblem

        # Get the module where the function is defined
        module = inspect.getmodule(route_after_next_subproblem)
        source = inspect.getsource(module)

        # Verify no backend.api imports
        assert "from backend.api" not in source
        assert "import backend.api" not in source

    def test_route_after_next_subproblem_returns_end_on_failure(self):
        """Verify router returns END (not raises) when sub-problems fail.

        When sub-problem results are incomplete, the router should return "END"
        and rely on EventCollector to publish the meeting_failed event.
        """
        from bo1.graph.routers.synthesis import route_after_next_subproblem
        from bo1.graph.state import DeliberationGraphState
        from bo1.models.problem import Problem, SubProblem

        # Create state with incomplete results (2 sub-problems, 1 result)
        problem = Problem(
            title="Test Problem",
            description="Test problem description",
            context="Test context",
            sub_problems=[
                SubProblem(id="sp-1", goal="Goal 1", context="Context 1", complexity_score=5),
                SubProblem(id="sp-2", goal="Goal 2", context="Context 2", complexity_score=5),
            ],
        )

        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=None,  # Signals loop termination
            sub_problem_results=[
                {"sub_problem_id": "sp-1", "synthesis": "Result 1"}
            ],  # Only 1 of 2 results
            personas=[],
            contributions=[],
            round_summaries=[],
            phase="synthesis",
            round_number=1,
            max_rounds=6,
            metrics=None,
        )

        # Router should return END (failure path)
        result = route_after_next_subproblem(state)
        assert result == "END"

    def test_route_after_next_subproblem_returns_meta_synthesis_on_success(self):
        """Verify router returns meta_synthesis when all sub-problems complete."""
        from bo1.graph.routers.synthesis import route_after_next_subproblem
        from bo1.graph.state import DeliberationGraphState
        from bo1.models.problem import Problem, SubProblem

        # Create state with all results present
        problem = Problem(
            title="Test Problem",
            description="Test problem description",
            context="Test context",
            sub_problems=[
                SubProblem(id="sp-1", goal="Goal 1", context="Context 1", complexity_score=5),
                SubProblem(id="sp-2", goal="Goal 2", context="Context 2", complexity_score=5),
            ],
        )

        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=None,  # Signals loop termination
            sub_problem_results=[
                {"sub_problem_id": "sp-1", "synthesis": "Result 1"},
                {"sub_problem_id": "sp-2", "synthesis": "Result 2"},
            ],  # All 2 results present
            personas=[],
            contributions=[],
            round_summaries=[],
            phase="synthesis",
            round_number=1,
            max_rounds=6,
            metrics=None,
        )

        # Router should return meta_synthesis (success path)
        result = route_after_next_subproblem(state)
        assert result == "meta_synthesis"
