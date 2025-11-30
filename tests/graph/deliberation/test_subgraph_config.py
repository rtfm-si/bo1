"""Tests for subgraph configuration and structure."""

from bo1.graph.deliberation.subgraph.config import (
    create_subproblem_graph,
    get_subproblem_graph,
    reset_subproblem_graph,
)


class TestCreateSubproblemGraph:
    """Tests for subgraph creation."""

    def test_creates_compiled_graph(self):
        """Should create a compiled graph instance."""
        graph = create_subproblem_graph()
        assert graph is not None
        # Check it's a compiled graph by checking for ainvoke method
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

    def test_graph_has_expected_nodes(self):
        """Graph should contain all required nodes."""
        graph = create_subproblem_graph()

        # Get node names from the graph
        node_names = set(graph.get_graph().nodes.keys())

        expected_nodes = {
            "select_personas",
            "parallel_round",
            "check_convergence",
            "vote",
            "synthesize",
            "__start__",
            "__end__",
        }

        # All expected nodes should be present
        for node in expected_nodes:
            assert node in node_names, f"Missing node: {node}"


class TestGetSubproblemGraph:
    """Tests for singleton graph access."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_subproblem_graph()

    def test_returns_same_instance(self):
        """Should return the same graph instance on multiple calls."""
        graph1 = get_subproblem_graph()
        graph2 = get_subproblem_graph()
        assert graph1 is graph2

    def test_reset_creates_new_instance(self):
        """Reset should cause next call to create new instance."""
        graph1 = get_subproblem_graph()
        reset_subproblem_graph()
        graph2 = get_subproblem_graph()
        assert graph1 is not graph2


class TestSubgraphRouting:
    """Tests for subgraph conditional routing."""

    def test_route_after_round_goes_to_convergence(self):
        """Should route to convergence check when under max rounds."""
        from bo1.graph.deliberation.subgraph.routers import route_after_round
        from bo1.graph.deliberation.subgraph.state import SubProblemGraphState

        state: SubProblemGraphState = {
            "round_number": 2,
            "max_rounds": 6,
        }

        result = route_after_round(state)
        assert result == "check_convergence"

    def test_route_after_round_goes_to_vote_when_max_rounds(self):
        """Should route to vote when max rounds exceeded."""
        from bo1.graph.deliberation.subgraph.routers import route_after_round
        from bo1.graph.deliberation.subgraph.state import SubProblemGraphState

        state: SubProblemGraphState = {
            "round_number": 7,
            "max_rounds": 6,
        }

        result = route_after_round(state)
        assert result == "vote"

    def test_route_after_convergence_continues_when_not_converged(self):
        """Should continue rounds when not converged."""
        from bo1.graph.deliberation.subgraph.routers import route_after_convergence
        from bo1.graph.deliberation.subgraph.state import SubProblemGraphState

        state: SubProblemGraphState = {
            "should_stop": False,
            "round_number": 3,
            "max_rounds": 6,
        }

        result = route_after_convergence(state)
        assert result == "parallel_round"

    def test_route_after_convergence_goes_to_vote_when_converged(self):
        """Should go to vote when converged."""
        from bo1.graph.deliberation.subgraph.routers import route_after_convergence
        from bo1.graph.deliberation.subgraph.state import SubProblemGraphState

        state: SubProblemGraphState = {
            "should_stop": True,
            "round_number": 4,
            "max_rounds": 6,
        }

        result = route_after_convergence(state)
        assert result == "vote"
