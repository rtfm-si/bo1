"""Research request consolidation for efficient batching.

Consolidates multiple related research requests into single API calls
to reduce costs and improve response time.

Example:
    "competitor pricing" + "competitor features" → 1 combined API call
    instead of 2 separate calls
"""

import logging
from typing import Any

from bo1.llm.embeddings import cosine_similarity, generate_embedding

logger = logging.getLogger(__name__)


def consolidate_research_requests(
    questions: list[dict[str, Any]],
    similarity_threshold: float = 0.75,
) -> list[list[dict[str, Any]]]:
    """Consolidate similar research requests into batches.

    Uses semantic similarity to detect related queries that can be combined
    into a single research API call.

    Args:
        questions: List of research questions with metadata
            Format: [{"question": "...", "priority": "...", "reason": "..."}]
        similarity_threshold: Cosine similarity threshold for grouping (0.75 = 75% similar)

    Returns:
        List of question batches, where each batch can be combined into one query
        Format: [[q1, q2], [q3], [q4, q5]] where q1+q2 should be combined

    Example:
        >>> questions = [
        ...     {"question": "What is competitor pricing?", "priority": "CRITICAL"},
        ...     {"question": "What are competitor features?", "priority": "CRITICAL"},
        ...     {"question": "What is market size?", "priority": "NICE_TO_HAVE"},
        ... ]
        >>> batches = consolidate_research_requests(questions, similarity_threshold=0.75)
        >>> len(batches)
        2  # [q1+q2], [q3]
    """
    if not questions:
        return []

    # Generate embeddings for all questions
    embeddings: list[list[float]] = []
    for q in questions:
        try:
            embedding = generate_embedding(q["question"], input_type="query")
            embeddings.append(embedding)
        except Exception as e:
            logger.warning(f"Failed to generate embedding for '{q['question'][:50]}...': {e}")
            # Use zero vector as fallback (will not match anything)
            embeddings.append([0.0] * 1024)

    # Group questions by similarity using simple clustering
    batches: list[list[dict[str, Any]]] = []
    used_indices: set[int] = set()

    for i, question in enumerate(questions):
        if i in used_indices:
            continue

        # Start new batch with this question
        batch = [question]
        used_indices.add(i)

        # Find similar questions to add to this batch
        for j, other_question in enumerate(questions):
            if j in used_indices or j == i:
                continue

            # Calculate similarity
            similarity = cosine_similarity(embeddings[i], embeddings[j])

            if similarity >= similarity_threshold:
                batch.append(other_question)
                used_indices.add(j)
                logger.debug(
                    f"Consolidated '{question['question'][:30]}...' + "
                    f"'{other_question['question'][:30]}...' (similarity={similarity:.3f})"
                )

        batches.append(batch)

    # Log consolidation stats
    original_count = len(questions)
    consolidated_count = len(batches)
    if original_count > consolidated_count:
        logger.info(
            f"Research consolidation: {original_count} requests → {consolidated_count} batches "
            f"({original_count - consolidated_count} requests consolidated, "
            f"{(1 - consolidated_count / original_count):.0%} reduction)"
        )

    return batches


def merge_batch_questions(batch: list[dict[str, Any]]) -> str:
    """Merge multiple questions into a single combined query.

    Args:
        batch: List of question dicts to merge

    Returns:
        Combined query string that covers all questions in batch

    Example:
        >>> batch = [
        ...     {"question": "What is competitor pricing?"},
        ...     {"question": "What are competitor features?"},
        ... ]
        >>> merge_batch_questions(batch)
        'competitor pricing and features'
    """
    if len(batch) == 1:
        return str(batch[0]["question"])

    # Extract questions
    questions = [q["question"] for q in batch]

    # Simple merging strategy: combine with "and"
    # For production, could use LLM to create better combined query
    combined = " and ".join(
        q.lower().replace("what is ", "").replace("what are ", "") for q in questions
    )

    logger.debug(f"Merged {len(batch)} questions into: '{combined}'")

    return combined


def split_batch_results(
    combined_result: dict[str, Any],
    original_batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Split combined research result back into individual results.

    Args:
        combined_result: Research result from combined query
        original_batch: Original question batch

    Returns:
        List of individual results (one per original question)

    Example:
        >>> combined_result = {
        ...     "summary": "Competitors charge $99/mo with feature X, Y, Z",
        ...     "sources": ["url1", "url2"],
        ... }
        >>> original_batch = [
        ...     {"question": "What is competitor pricing?"},
        ...     {"question": "What are competitor features?"},
        ... ]
        >>> results = split_batch_results(combined_result, original_batch)
        >>> len(results)
        2
    """
    # For now, return the same result for all questions in batch
    # Future enhancement: Use LLM to extract relevant portions for each question
    results = []
    for q in original_batch:
        results.append(
            {
                "question": q["question"],
                "summary": combined_result.get("summary", ""),
                "sources": combined_result.get("sources", []),
                "confidence": combined_result.get("confidence", "medium"),
                "cached": combined_result.get("cached", False),
                "cost": combined_result.get("cost", 0.0) / len(original_batch),  # Split cost evenly
                "consolidated": True,  # Mark as consolidated result
            }
        )

    return results
