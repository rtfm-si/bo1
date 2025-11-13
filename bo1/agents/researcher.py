"""Research agent for external information gathering.

STUB for Day 14 - Full implementation in Week 4 (Day 27).

Will integrate web search (Brave Search API / Tavily) + content extraction + summarization
to answer external research questions during deliberation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResearcherAgent:
    """Agent for researching external information gaps.

    **STUB**: Placeholder for Week 4 implementation.

    Future features:
    - Web search integration (Brave Search API / Tavily)
    - Content extraction from search results
    - Haiku-based summarization (200-300 tokens)
    - Source citations
    - Cost tracking

    Examples:
        >>> agent = ResearcherAgent()
        >>> result = await agent.research_question("What is average B2B SaaS churn rate?")
        >>> print(result["summary"])  # Will work in Week 4
    """

    def __init__(self) -> None:
        """Initialize the researcher agent (stub)."""
        logger.info("ResearcherAgent initialized (stub - full implementation Week 4)")

    async def research_questions(self, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Research a list of external questions.

        **STUB**: Currently just logs and returns placeholder data.

        Week 4 implementation will:
        1. Search the web for each question
        2. Extract relevant information from top results
        3. Summarize findings (200-300 tokens)
        4. Include sources/citations
        5. Track costs (search API + LLM summarization)

        Args:
            questions: List of external gaps from identify_information_gaps()
                Format: [{"question": "...", "priority": "...", "reason": "..."}]

        Returns:
            List of research results:
            [
                {
                    "question": "...",
                    "summary": "...",  # 200-300 token summary
                    "sources": ["url1", "url2"],  # Citations
                    "confidence": "high|medium|low"  # Quality of sources
                }
            ]

        Examples:
            >>> agent = ResearcherAgent()
            >>> questions = [
            ...     {"question": "What is average SaaS churn rate?", "priority": "CRITICAL", ...}
            ... ]
            >>> results = await agent.research_questions(questions)
        """
        if not questions:
            logger.info("No external questions to research")
            return []

        logger.info(f"[STUB] Would research {len(questions)} external questions:")
        for i, q in enumerate(questions, 1):
            question_text = q.get("question", "Unknown question")
            priority = q.get("priority", "UNKNOWN")
            logger.info(f"  {i}. [{priority}] {question_text}")

        logger.info("[STUB] Research functionality will be implemented in Week 4 (Day 27)")

        # Return placeholder results
        results = []
        for q in questions:
            results.append(
                {
                    "question": q.get("question", ""),
                    "summary": "[Research pending - Week 4 implementation]",
                    "sources": [],
                    "confidence": "stub",
                }
            )

        return results

    def format_research_context(self, research_results: list[dict[str, Any]]) -> str:
        """Format research results for inclusion in deliberation prompts.

        Args:
            research_results: List of research results from research_questions()

        Returns:
            Formatted string for prompt inclusion

        Examples:
            >>> agent = ResearcherAgent()
            >>> results = [{"question": "...", "summary": "...", "sources": [...]}]
            >>> formatted = agent.format_research_context(results)
        """
        if not research_results:
            return ""

        lines = ["<external_research>"]

        for result in research_results:
            question = result.get("question", "")
            summary = result.get("summary", "")
            sources = result.get("sources", [])
            confidence = result.get("confidence", "unknown")

            lines.append("  <research_item>")
            lines.append(f"    <question>{question}</question>")
            lines.append(f'    <findings confidence="{confidence}">')
            lines.append(f"      {summary}")
            lines.append("    </findings>")

            if sources:
                lines.append("    <sources>")
                for source in sources:
                    lines.append(f"      <source>{source}</source>")
                lines.append("    </sources>")

            lines.append("  </research_item>")

        lines.append("</external_research>")

        return "\n".join(lines)
