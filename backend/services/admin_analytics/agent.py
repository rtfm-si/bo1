"""Admin analytics agent — orchestrates plan → SQL → execute → chart → summarize.

Plain Python orchestrator (not LangGraph). Yields SSE event dicts
for streaming to the frontend.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

from bo1.llm.client import ClaudeClient
from bo1.llm.cost_tracker import CostTracker
from bo1.prompts.admin_analytics import (
    FOLLOW_UP_SYSTEM,
    PLANNER_SYSTEM,
    SUMMARIZER_SYSTEM,
    get_sql_generator_system,
)
from bo1.state.database import db_session

from .chart_recommender import recommend_chart
from .schema_context import get_schema_context
from .sql_safety import MAX_RESULT_ROWS, SQLValidationError, validate_sql

logger = logging.getLogger(__name__)

# Max rows sent to frontend (full data used for chart gen)
FRONTEND_ROW_LIMIT = 200


class AdminAnalyticsAgent:
    """Orchestrates multi-step analytics queries."""

    def __init__(self, model_preference: str = "sonnet") -> None:
        """Initialize with model preference for SQL generation."""
        self.client = ClaudeClient()
        self.model_preference = model_preference  # For SQL gen
        self.total_cost = 0.0

    async def run(
        self,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
        admin_user_id: str = "admin",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run the full analytics pipeline, yielding SSE events.

        Events:
            thinking: Planning phase started
            step_start: Beginning a step
            sql: Generated SQL for a step
            data: Query results summary
            chart: Plotly figure_json
            step_summary: Key findings for a step
            step_complete: Step finished
            suggestions: Follow-up question suggestions
            done: All steps complete
            error: Error occurred

        Args:
            question: Natural language question
            conversation_history: Previous Q&A messages for context
            admin_user_id: Admin user ID for cost tracking

        Yields:
            SSE event dicts with 'event' and 'data' keys
        """
        start_time = time.time()
        self.total_cost = 0.0

        try:
            # Phase 1: Plan
            yield {"event": "thinking", "data": {"status": "planning"}}
            steps = await self._plan(question, conversation_history)

            if not steps:
                yield {
                    "event": "error",
                    "data": {"error": "Could not decompose question into analysis steps"},
                }
                return

            yield {"event": "thinking", "data": {"status": "executing", "step_count": len(steps)}}

            all_results: list[dict[str, Any]] = []

            # Phase 2: Execute each step
            for i, step in enumerate(steps):
                step_desc = step.get("description", f"Step {i + 1}")
                yield {"event": "step_start", "data": {"step": i, "description": step_desc}}

                try:
                    # Generate SQL
                    sql = await self._generate_sql(step_desc, question, conversation_history)
                    yield {"event": "sql", "data": {"step": i, "sql": sql}}

                    # Validate SQL
                    safe_sql = validate_sql(sql)

                    # Execute
                    columns, rows = self._execute_sql(safe_sql)
                    row_count = len(rows)

                    yield {
                        "event": "data",
                        "data": {
                            "step": i,
                            "columns": columns,
                            "row_count": row_count,
                            "rows": rows[:FRONTEND_ROW_LIMIT],  # Cap for frontend
                        },
                    }

                    # Chart recommendation
                    chart = recommend_chart(columns, rows, step_desc)
                    if chart:
                        yield {"event": "chart", "data": {"step": i, "figure_json": chart}}

                    # Summarize step
                    summary = await self._summarize_step(step_desc, columns, rows[:50], question)
                    yield {"event": "step_summary", "data": {"step": i, "summary": summary}}

                    all_results.append(
                        {
                            "step": i,
                            "description": step_desc,
                            "sql": safe_sql,
                            "columns": columns,
                            "row_count": row_count,
                            "chart_config": chart,
                            "summary": summary,
                        }
                    )

                except SQLValidationError as e:
                    yield {
                        "event": "step_summary",
                        "data": {
                            "step": i,
                            "summary": f"SQL validation error: {e}",
                        },
                    }
                    all_results.append(
                        {
                            "step": i,
                            "description": step_desc,
                            "error": str(e),
                        }
                    )
                except Exception as e:
                    logger.exception(f"Step {i} failed: {e}")
                    yield {
                        "event": "step_summary",
                        "data": {
                            "step": i,
                            "summary": f"Query error: {e}",
                        },
                    }
                    all_results.append(
                        {
                            "step": i,
                            "description": step_desc,
                            "error": str(e),
                        }
                    )

                yield {"event": "step_complete", "data": {"step": i}}

            # Phase 3: Suggest follow-ups
            suggestions = await self._suggest_follow_ups(question, all_results)
            if suggestions:
                yield {"event": "suggestions", "data": {"suggestions": suggestions}}

            # Track cost
            elapsed = time.time() - start_time
            self._track_cost(admin_user_id, question)

            yield {
                "event": "done",
                "data": {
                    "steps": all_results,
                    "total_cost": round(self.total_cost, 6),
                    "elapsed_seconds": round(elapsed, 2),
                    "suggestions": suggestions,
                },
            }

        except Exception as e:
            logger.exception(f"Analytics agent error: {e}")
            yield {"event": "error", "data": {"error": str(e)}}

    async def _plan(
        self,
        question: str,
        history: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """Decompose question into analysis steps using Haiku."""
        messages = []
        if history:
            for msg in history[-6:]:  # Last 3 exchanges
                messages.append(msg)
        messages.append({"role": "user", "content": question})

        response, usage = await self.client.call(
            model="haiku",
            system=PLANNER_SYSTEM,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            prefill="[",
        )

        self.total_cost += usage.calculate_cost("haiku")

        try:
            text = "[" + response if not response.startswith("[") else response
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse planner response: {response[:200]}")
            # Fallback: single step with original question
            return [{"description": question, "expected_output": "query result"}]

    async def _generate_sql(
        self,
        step_description: str,
        original_question: str,
        history: list[dict[str, str]] | None,
    ) -> str:
        """Generate SQL for a single step using configured model."""
        schema = get_schema_context()
        system = get_sql_generator_system(schema)

        prompt = f"Original question: {original_question}\n\nCurrent step: {step_description}\n\nWrite the SQL query."
        messages = [{"role": "user", "content": prompt}]

        response, usage = await self.client.call(
            model=self.model_preference,
            system=system,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            cache_system=True,
        )

        self.total_cost += usage.calculate_cost(self.model_preference)

        # Clean markdown fences if present
        sql = response.strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        return sql.strip()

    def _execute_sql(self, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
        """Execute validated SQL in read-only transaction with timeout.

        Returns:
            (column_names, list_of_row_dicts)
        """
        with db_session(statement_timeout_ms=15_000) as conn:
            with conn.cursor() as cur:
                # Force read-only transaction
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute(sql)

                if cur.description is None:
                    return [], []

                columns = [desc[0] for desc in cur.description]
                rows_raw = cur.fetchmany(MAX_RESULT_ROWS)

                rows = []
                for row_tuple in rows_raw:
                    row_dict: dict[str, Any] = {}
                    for j, col in enumerate(columns):
                        val = row_tuple[j]
                        # JSON-serialize special types
                        if hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif isinstance(val, (bytes, memoryview)):
                            val = str(val)
                        elif isinstance(val, Decimal):
                            val = float(val)
                        row_dict[col] = val
                    rows.append(row_dict)

                return columns, rows

    async def _summarize_step(
        self,
        step_description: str,
        columns: list[str],
        rows: list[dict],
        original_question: str,
    ) -> str:
        """Summarize step results using Haiku."""
        if not rows:
            return "No results returned for this query."

        # Build compact data preview
        preview = json.dumps(rows[:10], default=str)
        if len(preview) > 2000:
            preview = preview[:2000] + "..."

        prompt = (
            f"Question: {original_question}\n"
            f"Step: {step_description}\n"
            f"Columns: {', '.join(columns)}\n"
            f"Row count: {len(rows)}\n"
            f"Sample data:\n{preview}"
        )

        response, usage = await self.client.call(
            model="haiku",
            system=SUMMARIZER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )

        self.total_cost += usage.calculate_cost("haiku")
        return response.strip()

    async def _suggest_follow_ups(
        self,
        question: str,
        results: list[dict[str, Any]],
    ) -> list[str]:
        """Suggest follow-up questions using Haiku."""
        summaries = []
        for r in results:
            if "summary" in r:
                summaries.append(f"- {r.get('description', '')}: {r['summary']}")

        prompt = f"Original question: {question}\n\nResults:\n" + "\n".join(summaries)

        try:
            response, usage = await self.client.call(
                model="haiku",
                system=FOLLOW_UP_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=512,
                prefill="[",
            )
            self.total_cost += usage.calculate_cost("haiku")

            text = "[" + response if not response.startswith("[") else response
            return json.loads(text)
        except Exception:
            return []

    def _track_cost(self, admin_user_id: str, question: str) -> None:
        """Log total cost for this analytics query."""
        if self.total_cost > 0:
            try:
                CostTracker.log_cost(
                    session_id=f"admin_analytics_{uuid.uuid4().hex[:8]}",
                    user_id=admin_user_id,
                    provider="anthropic",
                    model=self.model_preference,
                    prompt_type="admin_analytics",
                    total_cost=self.total_cost,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    feature="admin_analytics_chat",
                    cost_category="internal_system",
                    metadata={"question": question[:200]},
                )
            except Exception as e:
                logger.debug(f"Failed to track analytics cost: {e}")
