"""Contribution summarization service for Board of One.

Provides AI-powered summarization of expert contributions using Claude Haiku.
Extracted from EventCollector for better testability and separation of concerns.
"""

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING

import httpx
from anthropic import APIConnectionError, APIError, RateLimitError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bo1.config import resolve_model_alias
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.models import ContributionSummary
from bo1.utils.json_parsing import parse_json_with_fallback

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# Concurrency limit for parallel summarization calls (prevents API rate limit errors)
SUMMARIZATION_CONCURRENCY_LIMIT = 5


class ContributionSummarizer:
    """AI-powered contribution summarization service.

    Uses Claude Haiku for cost-effective summarization (~$0.001 per contribution).
    Includes retry logic and fallback handling for robustness.

    Args:
        client: AsyncAnthropic client instance (injectable for testing)
    """

    def __init__(self, client: "AsyncAnthropic") -> None:
        """Initialize with Anthropic client."""
        self.client = client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(
            (APIError, RateLimitError, APIConnectionError, httpx.ConnectError)
        ),
        before_sleep=lambda rs: logger.debug(
            f"Retrying summarization LLM call (attempt {rs.attempt_number}): "
            f"{rs.outcome.exception()}"
        ),
        reraise=True,
    )
    async def _call_llm(self, prompt: str, persona_name: str) -> tuple[str, bool]:
        """Call the summarization LLM with retry logic.

        Args:
            prompt: The formatted prompt for summarization
            persona_name: Expert name for cost tracking

        Returns:
            Tuple of (response_text, was_truncated)

        Raises:
            APIError, RateLimitError, APIConnectionError: After retries exhausted
        """
        ctx = get_cost_context()
        model = resolve_model_alias("haiku")

        with CostTracker.track_call(
            provider="anthropic",
            operation_type="completion",
            model_name=model,
            session_id=ctx.get("session_id"),
            user_id=ctx.get("user_id"),
            node_name="contribution_summarizer",
            phase=ctx.get("phase"),
            persona_name=persona_name,
            round_number=ctx.get("round_number"),
            sub_problem_index=ctx.get("sub_problem_index"),
        ) as cost_record:
            response = await self.client.messages.create(
                model=model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "{"},  # Prefill to force JSON
                ],
            )

            cost_record.input_tokens = response.usage.input_tokens
            cost_record.output_tokens = response.usage.output_tokens

        was_truncated = response.stop_reason == "max_tokens"
        if was_truncated:
            logger.warning(
                f"Summarization truncated for {persona_name}: "
                f"stop_reason=max_tokens, output_tokens={response.usage.output_tokens}"
            )

        return response.content[0].text, was_truncated

    async def summarize(self, content: str, persona_name: str) -> dict | None:
        """Summarize expert contribution into structured insights.

        Args:
            content: Full expert contribution (200-500 words)
            persona_name: Expert name for context

        Returns:
            Dict with concise, looking_for, value_added, concerns, questions,
            or fallback dict if summarization fails
        """
        from backend.api.metrics import prom_metrics
        from bo1.prompts.contribution_summary_prompts import (
            compose_contribution_summary_request,
        )

        start_time = time.perf_counter()
        status = "success"

        try:
            prompt = compose_contribution_summary_request(content, persona_name)

            try:
                response_text, was_truncated = await self._call_llm(prompt, persona_name)
            except (
                APIError,
                RateLimitError,
                APIConnectionError,
                httpx.ConnectError,
                RetryError,
            ) as e:
                logger.warning(
                    f"Summarization LLM call failed after retries for {persona_name}: {e}"
                )
                status = "error"
                return self.create_fallback(persona_name, content)

            # Strategy 1: Try parse_json_with_fallback with prefill
            summary, parse_errors = parse_json_with_fallback(
                content=response_text,
                prefill="{",
                context=f"contribution summary for {persona_name}",
                logger=logger,
            )

            if summary is not None:
                return self.validate_schema(summary)

            # Strategy 2: Extract first complete JSON object using brace counting
            summary = self._extract_first_json_object("{" + response_text)
            if summary is not None:
                logger.debug(f"Extracted summary via brace counting for {persona_name}")
                return self.validate_schema(summary)

            # Strategy 3: Return fallback summary
            truncation_note = " (response was truncated)" if was_truncated else ""
            logger.warning(
                f"Failed to parse summary for {persona_name}: "
                f"{parse_errors}{truncation_note}. Using fallback."
            )
            status = "fallback"
            return self.create_fallback(persona_name, content)

        except Exception as e:
            logger.error(f"Failed to summarize contribution for {persona_name}: {e}")
            status = "error"
            return self.create_fallback(persona_name, content)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            prom_metrics.record_summarization_duration(persona_name, status, duration_ms)
            logger.debug(f"Summarization for {persona_name}: {duration_ms:.1f}ms ({status})")

    async def batch_summarize(self, items: list[tuple[str, str]]) -> list[dict | None]:
        """Summarize multiple contributions in parallel with concurrency limit.

        Args:
            items: List of (content, persona_name) tuples to summarize

        Returns:
            List of summary dicts in same order as input
        """
        from backend.api.metrics import prom_metrics

        if not items:
            return []

        batch_start = time.perf_counter()
        semaphore = asyncio.Semaphore(SUMMARIZATION_CONCURRENCY_LIMIT)

        async def limited_summarize(content: str, name: str) -> dict | None:
            async with semaphore:
                return await self.summarize(content, name)

        tasks = [limited_summarize(content, name) for content, name in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                persona_name = items[i][1]
                logger.error(f"Batch summarization failed for {persona_name}: {result}")
                summaries.append(self.create_fallback(persona_name, items[i][0]))
            else:
                summaries.append(result)

        batch_duration_ms = (time.perf_counter() - batch_start) * 1000
        prom_metrics.record_summarization_batch(len(items), batch_duration_ms)
        logger.info(
            f"Batch summarized {len(items)} contributions in {batch_duration_ms:.1f}ms "
            f"(concurrency={SUMMARIZATION_CONCURRENCY_LIMIT})"
        )
        return summaries

    def _extract_first_json_object(self, text: str) -> dict | None:
        """Extract first complete JSON object using brace counting.

        Args:
            text: Text potentially containing JSON object(s)

        Returns:
            Parsed dict if found, None otherwise
        """
        try:
            start = text.find("{")
            if start == -1:
                return None

            brace_count = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(text[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if char == "\\":
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start : i + 1]
                        return json.loads(json_str)

            return None
        except json.JSONDecodeError:
            return None

    def validate_schema(self, summary: dict) -> dict:
        """Validate summary against ContributionSummary schema.

        Args:
            summary: Parsed summary dict from LLM

        Returns:
            Validated summary dict with schema_valid flag
        """
        from pydantic import ValidationError

        try:
            validated = ContributionSummary(**summary)
            return validated.model_dump()
        except ValidationError as e:
            field_errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            logger.warning(f"Schema validation failed: {', '.join(field_errors)}")

            safe_summary = {
                "concise": str(summary.get("concise", ""))[:500],
                "looking_for": str(summary.get("looking_for", ""))[:200],
                "value_added": str(summary.get("value_added", ""))[:200],
                "concerns": (
                    summary.get("concerns", []) if isinstance(summary.get("concerns"), list) else []
                ),
                "questions": (
                    summary.get("questions", [])
                    if isinstance(summary.get("questions"), list)
                    else []
                ),
                "parse_error": False,
                "schema_valid": False,
            }
            return safe_summary

    def create_fallback(self, persona_name: str, content: str) -> dict:
        """Create a basic fallback summary when parsing fails.

        Args:
            persona_name: Expert name
            content: Original contribution content

        Returns:
            Basic summary dict matching ContributionSummary schema
        """
        first_sentence = content.split(".")[0][:100] if content else ""
        return {
            "concise": f"{first_sentence}..." if first_sentence else f"Analysis by {persona_name}",
            "looking_for": "Evaluating the situation",
            "value_added": "Expert perspective",
            "concerns": [],
            "questions": [],
            "parse_error": True,
            "schema_valid": False,
        }
