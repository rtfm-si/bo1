"""Data analysis agent for dataset analysis during deliberation.

Integrates:
- Query execution via datasets API endpoints
- Chart generation for visualizations
- Cost tracking for analysis operations
- XML-formatted context for LLM prompts
"""

import logging
from typing import Any

import httpx

from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostRecord, CostTracker

logger = logging.getLogger(__name__)


class DataAnalysisError(Exception):
    """Error during data analysis."""

    pass


class DataAnalysisAgent:
    """Agent for analyzing datasets during deliberation.

    Features:
    - Executes structured queries against datasets
    - Generates chart visualizations
    - Formats results for LLM context injection
    - Tracks costs for analysis operations

    Production Integration:
    - Used in bo1/graph/nodes/data_analysis.py during deliberation
    - Invoked via facilitator decision when data analysis is needed
    - Calls internal API endpoints for query/chart execution
    """

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        """Initialize the data analysis agent.

        Args:
            base_url: Base URL for API calls (defaults to internal API at port 8000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or "http://localhost:8000"
        self.timeout = timeout
        logger.info("DataAnalysisAgent initialized")

    async def analyze_dataset(
        self,
        dataset_id: str,
        questions: list[str],
        user_id: str,
        auth_token: str | None = None,
    ) -> list[dict[str, Any]]:
        """Analyze a dataset based on analysis questions.

        Args:
            dataset_id: UUID of the dataset to analyze
            questions: List of analysis questions (e.g., "What are top sales by region?")
            user_id: User ID for authorization
            auth_token: Optional auth token for API calls

        Returns:
            List of analysis results with query results and optional charts

        Examples:
            >>> agent = DataAnalysisAgent()
            >>> results = await agent.analyze_dataset(
            ...     dataset_id="abc-123",
            ...     questions=["What are the top 5 products by revenue?"],
            ...     user_id="user-456"
            ... )
        """
        if not questions:
            logger.info("No analysis questions provided")
            return []

        ctx = get_cost_context()
        results = []
        total_cost = 0.0

        for question in questions:
            try:
                result = await self._analyze_single_question(
                    dataset_id=dataset_id,
                    question=question,
                    user_id=user_id,
                    auth_token=auth_token,
                )
                results.append(result)
                total_cost += result.get("cost", 0.0)
            except DataAnalysisError as e:
                logger.warning(f"Analysis failed for question '{question[:50]}...': {e}")
                results.append(
                    {
                        "question": question,
                        "error": str(e),
                        "query_result": None,
                        "chart_result": None,
                        "cost": 0.0,
                    }
                )

        # Track total analysis cost
        if total_cost > 0:
            cost_record = CostRecord(
                provider="internal",
                model_name="data_analysis",
                operation_type="dataset_analysis",
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name=ctx.get("node_name", "data_analysis_node"),
                phase=ctx.get("phase"),
                total_cost=total_cost,
                status="success",
                metadata={
                    "dataset_id": dataset_id,
                    "question_count": len(questions),
                },
            )
            CostTracker.log_cost(cost_record)

        logger.info(
            f"Dataset analysis complete - {len(results)} questions, cost: ${total_cost:.4f}"
        )
        return results

    async def _analyze_single_question(
        self,
        dataset_id: str,
        question: str,
        user_id: str,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        """Analyze a single question against a dataset.

        Uses heuristics to determine appropriate query type and chart type
        based on the question text.

        Args:
            dataset_id: Dataset UUID
            question: Analysis question
            user_id: User ID
            auth_token: Optional auth token

        Returns:
            Analysis result dict with query_result, chart_result, cost
        """
        # Build query spec based on question heuristics
        query_spec = self._question_to_query_spec(question)

        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        query_result = None
        chart_result = None
        cost = 0.0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Execute query
            try:
                query_response = await client.post(
                    f"{self.base_url}/api/v1/datasets/{dataset_id}/query",
                    json=query_spec,
                    headers=headers,
                )
                if query_response.status_code == 200:
                    query_result = query_response.json()
                    cost += 0.001  # Nominal cost for query execution
                elif query_response.status_code == 404:
                    raise DataAnalysisError(f"Dataset {dataset_id} not found")
                elif query_response.status_code == 401:
                    raise DataAnalysisError("Unauthorized access to dataset")
                else:
                    logger.warning(
                        f"Query failed: {query_response.status_code} - {query_response.text}"
                    )
            except httpx.RequestError as e:
                logger.error(f"Query request failed: {e}")
                raise DataAnalysisError(f"Query request failed: {e}") from e

            # Generate chart if query succeeded and chart is appropriate
            if query_result and self._should_generate_chart(question, query_result):
                chart_spec = self._question_to_chart_spec(question, query_result)
                if chart_spec:
                    try:
                        chart_response = await client.post(
                            f"{self.base_url}/api/v1/datasets/{dataset_id}/chart",
                            json=chart_spec,
                            headers=headers,
                        )
                        if chart_response.status_code == 200:
                            chart_result = chart_response.json()
                            cost += 0.002  # Nominal cost for chart generation
                    except httpx.RequestError as e:
                        logger.warning(f"Chart request failed: {e}")

        return {
            "question": question,
            "query_result": query_result,
            "chart_result": chart_result,
            "cost": cost,
        }

    def _question_to_query_spec(self, question: str) -> dict[str, Any]:
        """Convert analysis question to QuerySpec.

        Uses simple heuristics to determine query type.

        Args:
            question: Analysis question text

        Returns:
            QuerySpec dict for API call
        """
        question_lower = question.lower()

        # Default to aggregate query (most common for analysis)
        query_type = "aggregate"

        # Detect trend queries
        if any(
            kw in question_lower
            for kw in ["over time", "trend", "by month", "by year", "by date", "growth"]
        ):
            query_type = "trend"

        # Detect comparison queries
        if any(kw in question_lower for kw in ["compare", "versus", "vs", "difference"]):
            query_type = "compare"

        # Detect correlation queries
        if any(kw in question_lower for kw in ["correlation", "relationship", "correlate"]):
            query_type = "correlate"

        # Detect filter-only queries
        if any(
            kw in question_lower for kw in ["show me", "list", "find", "which", "where"]
        ) and not any(kw in question_lower for kw in ["total", "sum", "average", "count", "top"]):
            query_type = "filter"

        return {
            "query_type": query_type,
            "limit": 100,
            "offset": 0,
        }

    def _should_generate_chart(self, question: str, query_result: dict[str, Any]) -> bool:
        """Determine if a chart should be generated for this result.

        Args:
            question: Original question
            query_result: Query result dict

        Returns:
            True if chart generation is appropriate
        """
        # Don't chart if too few rows
        if query_result.get("total_count", 0) < 2:
            return False

        # Chart if question mentions visualization keywords
        question_lower = question.lower()
        chart_keywords = ["chart", "graph", "visualize", "plot", "show", "trend", "top"]
        return any(kw in question_lower for kw in chart_keywords)

    def _question_to_chart_spec(
        self, question: str, query_result: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Convert question and result to ChartSpec.

        Args:
            question: Analysis question
            query_result: Query result to visualize

        Returns:
            ChartSpec dict or None if chart not appropriate
        """
        columns = query_result.get("columns", [])
        if len(columns) < 2:
            return None

        question_lower = question.lower()

        # Determine chart type
        chart_type = "bar"  # Default
        if "trend" in question_lower or "over time" in question_lower:
            chart_type = "line"
        elif "distribution" in question_lower or "percentage" in question_lower:
            chart_type = "pie"
        elif "scatter" in question_lower or "correlation" in question_lower:
            chart_type = "scatter"

        # Use first two columns as x and y
        x_field = columns[0]
        y_field = columns[1] if len(columns) > 1 else columns[0]

        return {
            "chart_type": chart_type,
            "x_field": x_field,
            "y_field": y_field,
            "title": question[:100],
            "width": 800,
            "height": 600,
        }

    def format_analysis_context(self, analysis_results: list[dict[str, Any]]) -> str:
        """Format analysis results for inclusion in deliberation prompts.

        Args:
            analysis_results: List of results from analyze_dataset()

        Returns:
            XML-formatted string for prompt inclusion
        """
        if not analysis_results:
            return ""

        lines = ["<dataset_analysis>"]

        for result in analysis_results:
            question = result.get("question", "")
            query_result = result.get("query_result")
            chart_result = result.get("chart_result")
            error = result.get("error")

            lines.append("  <analysis_item>")
            lines.append(f"    <question>{question}</question>")

            if error:
                lines.append(f"    <error>{error}</error>")
            elif query_result:
                rows = query_result.get("rows", [])
                columns = query_result.get("columns", [])
                total = query_result.get("total_count", 0)

                lines.append(f'    <data rows="{total}" columns="{len(columns)}">')

                # Format as simple table (limit to 10 rows for context)
                if rows:
                    lines.append(f"      <columns>{', '.join(columns)}</columns>")
                    for row in rows[:10]:
                        row_str = " | ".join(str(row.get(c, "")) for c in columns)
                        lines.append(f"      <row>{row_str}</row>")
                    if len(rows) > 10:
                        lines.append(f"      <note>Showing 10 of {total} rows</note>")

                lines.append("    </data>")

                if chart_result:
                    chart_type = chart_result.get("chart_type", "unknown")
                    lines.append(f'    <chart type="{chart_type}">Generated</chart>')

            lines.append("  </analysis_item>")

        lines.append("</dataset_analysis>")

        return "\n".join(lines)
