"""SEO Autopilot Service.

Automated topic discovery and article generation with purchase intent prioritization.
Runs on a schedule to generate high-intent content for users with autopilot enabled.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import text

from backend.services.content_generator import generate_blog_post
from backend.services.topic_discovery import Topic, discover_topics
from bo1.billing import PlanConfig
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


# =============================================================================
# Purchase Intent Scoring
# =============================================================================

# Transactional modifiers that indicate purchase intent
TRANSACTIONAL_MODIFIERS = [
    "buy",
    "purchase",
    "pricing",
    "cost",
    "price",
    "quote",
    "order",
    "subscribe",
    "trial",
    "free trial",
    "demo",
    "get started",
]

# Problem-solution patterns that indicate high intent
PROBLEM_SOLUTION_PATTERNS = [
    "how to",
    "best way to",
    "solution for",
    "solve",
    "fix",
    "improve",
    "increase",
    "reduce",
    "optimize",
    "automate",
]

# Comparison patterns that indicate decision-stage queries
COMPARISON_PATTERNS = [
    "vs",
    "versus",
    "compare",
    "comparison",
    "alternative",
    "alternatives to",
    "better than",
    "instead of",
    "review",
    "reviews",
]

# Decision-stage patterns
DECISION_STAGE_PATTERNS = [
    "best",
    "top",
    "which",
    "choose",
    "choosing",
    "select",
    "selection",
    "recommend",
    "recommendation",
]


@dataclass
class ScoredTopic:
    """Topic with purchase intent score."""

    topic: Topic
    intent_score: float  # 0.0 - 1.0
    intent_signals: list[str]  # Which signals were detected


def calculate_purchase_intent_score(topic: Topic) -> ScoredTopic:
    """Calculate purchase intent score for a topic.

    Scoring based on:
    - Transactional modifiers: +0.4
    - Problem-solution patterns: +0.3
    - Comparison patterns: +0.25
    - Decision-stage patterns: +0.2

    Maximum score: 1.0 (capped)

    Args:
        topic: Topic to score

    Returns:
        ScoredTopic with intent score and detected signals
    """
    score = 0.0
    signals: list[str] = []

    # Combine title, description, and keywords for matching
    text_to_check = " ".join(
        [topic.title.lower(), topic.description.lower(), " ".join(topic.keywords).lower()]
    )

    # Check transactional modifiers
    for modifier in TRANSACTIONAL_MODIFIERS:
        if modifier in text_to_check:
            score += 0.4
            signals.append(f"transactional:{modifier}")
            break  # Only count once per category

    # Check problem-solution patterns
    for pattern in PROBLEM_SOLUTION_PATTERNS:
        if pattern in text_to_check:
            score += 0.3
            signals.append(f"problem-solution:{pattern}")
            break

    # Check comparison patterns
    for pattern in COMPARISON_PATTERNS:
        if pattern in text_to_check:
            score += 0.25
            signals.append(f"comparison:{pattern}")
            break

    # Check decision-stage patterns
    for pattern in DECISION_STAGE_PATTERNS:
        if pattern in text_to_check:
            score += 0.2
            signals.append(f"decision-stage:{pattern}")
            break

    # Cap at 1.0
    score = min(score, 1.0)

    return ScoredTopic(topic=topic, intent_score=score, intent_signals=signals)


def filter_high_intent_topics(
    topics: list[Topic],
    min_intent_score: float = 0.3,
    top_percentile: float = 0.2,  # Top 20%
) -> list[ScoredTopic]:
    """Filter topics to only high-intent ones.

    Args:
        topics: List of topics to filter
        min_intent_score: Minimum intent score threshold
        top_percentile: Return top X% of scored topics (default 20%)

    Returns:
        Filtered and sorted list of ScoredTopic objects
    """
    # Score all topics
    scored_topics = [calculate_purchase_intent_score(t) for t in topics]

    # Filter by minimum score
    filtered = [st for st in scored_topics if st.intent_score >= min_intent_score]

    # Sort by intent score descending
    sorted_topics = sorted(filtered, key=lambda st: st.intent_score, reverse=True)

    # Take top percentile
    top_count = max(1, int(len(sorted_topics) * top_percentile))
    return sorted_topics[:top_count]


# =============================================================================
# Autopilot Service
# =============================================================================


@dataclass
class AutopilotCycleResult:
    """Result of an autopilot cycle run."""

    topics_discovered: int
    articles_generated: int
    articles_queued: int
    articles_published: int
    tier_limit_reached: bool
    errors: list[str]


class SEOAutopilotService:
    """Service for automated SEO content generation.

    Runs scheduled cycles that:
    1. Discover high-intent topics based on user's industry/keywords
    2. Generate articles for top-scoring topics
    3. Queue for review or auto-publish based on config
    """

    def __init__(self, user_id: str, workspace_id: str | None = None):
        """Initialize autopilot service.

        Args:
            user_id: User ID to run autopilot for
            workspace_id: Optional workspace ID
        """
        self.user_id = user_id
        self.workspace_id = workspace_id
        self._config: dict | None = None
        self._tier: str | None = None

    async def _load_config(self) -> dict:
        """Load autopilot config from database."""
        if self._config is not None:
            return self._config

        with db_session() as session:
            result = session.execute(
                text("""
                    SELECT seo_autopilot_config, context_data
                    FROM user_context
                    WHERE user_id = :user_id
                """),
                {"user_id": self.user_id},
            )
            row = result.fetchone()

        if row and row[0]:
            self._config = row[0]
        else:
            self._config = {
                "enabled": False,
                "frequency_per_week": 1,
                "auto_publish": False,
                "require_approval": True,
                "target_keywords": [],
                "purchase_intent_only": True,
            }

        return self._config

    async def _get_tier(self) -> str:
        """Get user's subscription tier."""
        if self._tier is not None:
            return self._tier

        with db_session() as session:
            result = session.execute(
                text("SELECT subscription_tier FROM users WHERE id = :user_id"),
                {"user_id": self.user_id},
            )
            row = result.fetchone()

        self._tier = row[0] if row and row[0] else "free"
        return self._tier

    async def _get_monthly_article_count(self) -> int:
        """Get number of articles generated this month."""
        with db_session() as session:
            result = session.execute(
                text("""
                    SELECT COUNT(*) FROM seo_blog_articles
                    WHERE user_id = :user_id
                    AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
                """),
                {"user_id": self.user_id},
            )
            row = result.fetchone()
        return row[0] if row else 0

    async def _get_industry(self) -> str | None:
        """Get user's industry from context."""
        with db_session() as session:
            result = session.execute(
                text("""
                    SELECT context_data->>'industry'
                    FROM user_context
                    WHERE user_id = :user_id
                """),
                {"user_id": self.user_id},
            )
            row = result.fetchone()
        return row[0] if row else None

    async def _get_existing_topic_keywords(self) -> list[str]:
        """Get keywords from existing topics to avoid duplicates."""
        with db_session() as session:
            result = session.execute(
                text("""
                    SELECT keyword FROM seo_topics
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 50
                """),
                {"user_id": self.user_id},
            )
            rows = result.fetchall()
        return [row[0] for row in rows]

    async def _create_topic(self, topic: Topic) -> int | None:
        """Create a topic in the database.

        Args:
            topic: Topic to create

        Returns:
            Topic ID if created, None if error
        """
        try:
            with db_session() as session:
                result = session.execute(
                    text("""
                        INSERT INTO seo_topics
                        (user_id, workspace_id, keyword, status, notes)
                        VALUES (:user_id, :workspace_id, :keyword, 'researched', :notes)
                        RETURNING id
                    """),
                    {
                        "user_id": self.user_id,
                        "workspace_id": self.workspace_id,
                        "keyword": topic.title,
                        "notes": f"Autopilot: {topic.description} | Keywords: {', '.join(topic.keywords)}",
                    },
                )
                row = result.fetchone()
                session.commit()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to create topic: {e}")
            return None

    async def _create_article(self, topic_id: int, keyword: str, auto_publish: bool) -> int | None:
        """Generate and save an article.

        Args:
            topic_id: Source topic ID
            keyword: Primary keyword for article
            auto_publish: Whether to auto-publish or queue for review

        Returns:
            Article ID if created, None if error
        """
        try:
            # Generate blog content
            blog_content = await generate_blog_post(keyword, [keyword])

            status = "published" if auto_publish else "pending_review"

            with db_session() as session:
                result = session.execute(
                    text("""
                        INSERT INTO seo_blog_articles
                        (user_id, workspace_id, topic_id, title, excerpt, content,
                         meta_title, meta_description, status)
                        VALUES (:user_id, :workspace_id, :topic_id, :title, :excerpt,
                                :content, :meta_title, :meta_description, :status)
                        RETURNING id
                    """),
                    {
                        "user_id": self.user_id,
                        "workspace_id": self.workspace_id,
                        "topic_id": topic_id,
                        "title": blog_content.title,
                        "excerpt": blog_content.excerpt,
                        "content": blog_content.content,
                        "meta_title": blog_content.meta_title,
                        "meta_description": blog_content.meta_description,
                        "status": status,
                    },
                )
                row = result.fetchone()

                # Update topic status
                session.execute(
                    text("""
                        UPDATE seo_topics SET status = 'writing', updated_at = now()
                        WHERE id = :id
                    """),
                    {"id": topic_id},
                )
                session.commit()

                return row[0] if row else None

        except Exception as e:
            logger.error(f"Failed to generate article for topic {topic_id}: {e}")
            return None

    async def discover_high_intent_topics(self) -> list[ScoredTopic]:
        """Discover topics filtered by purchase intent.

        Returns:
            List of high-intent topics sorted by score
        """
        config = await self._load_config()

        industry = await self._get_industry()
        existing_keywords = await self._get_existing_topic_keywords()
        target_keywords = config.get("target_keywords", [])

        # Discover topics
        topics = await discover_topics(
            industry=industry,
            focus_areas=target_keywords or None,
            existing_topics=existing_keywords,
        )

        if not topics:
            logger.info(f"No topics discovered for user {self.user_id[:8]}...")
            return []

        # Filter by purchase intent if enabled
        purchase_intent_only = config.get("purchase_intent_only", True)

        if purchase_intent_only:
            scored_topics = filter_high_intent_topics(topics)
            logger.info(
                f"Filtered {len(topics)} topics to {len(scored_topics)} high-intent "
                f"for user {self.user_id[:8]}..."
            )
            return scored_topics
        else:
            # Return all topics with their scores
            return [calculate_purchase_intent_score(t) for t in topics]

    async def run_scheduled_cycle(self) -> AutopilotCycleResult:
        """Run a scheduled autopilot cycle.

        Main entry point for the scheduled job.
        Discovers topics, generates articles, and respects tier limits.

        Returns:
            AutopilotCycleResult with stats
        """
        result = AutopilotCycleResult(
            topics_discovered=0,
            articles_generated=0,
            articles_queued=0,
            articles_published=0,
            tier_limit_reached=False,
            errors=[],
        )

        config = await self._load_config()

        # Check if autopilot is enabled
        if not config.get("enabled", False):
            logger.debug(f"Autopilot not enabled for user {self.user_id[:8]}...")
            return result

        tier = await self._get_tier()

        # Check tier limits
        limit = PlanConfig.get_seo_articles_limit(tier)
        current_usage = await self._get_monthly_article_count()

        if not PlanConfig.is_unlimited(limit) and current_usage >= limit:
            logger.info(
                f"Autopilot tier limit reached for user {self.user_id[:8]}... "
                f"({current_usage}/{limit})"
            )
            result.tier_limit_reached = True
            return result

        # Discover high-intent topics
        try:
            scored_topics = await self.discover_high_intent_topics()
            result.topics_discovered = len(scored_topics)
        except Exception as e:
            logger.error(f"Topic discovery failed for user {self.user_id[:8]}...: {e}")
            result.errors.append(f"Topic discovery failed: {e}")
            return result

        if not scored_topics:
            logger.info(f"No topics to process for user {self.user_id[:8]}...")
            return result

        # Determine how many articles to generate this cycle
        auto_publish = config.get("auto_publish", False)
        # Note: frequency_per_week controls scheduling frequency, not batch size per cycle

        # Generate 1 article per cycle (scheduler runs frequency_per_week times per week)
        articles_to_generate = 1

        # Respect tier limits
        remaining_quota = limit - current_usage if not PlanConfig.is_unlimited(limit) else 999
        articles_to_generate = min(articles_to_generate, remaining_quota)

        if articles_to_generate <= 0:
            result.tier_limit_reached = True
            return result

        # Generate articles for top topics
        for scored_topic in scored_topics[:articles_to_generate]:
            topic_id = await self._create_topic(scored_topic.topic)
            if not topic_id:
                result.errors.append(f"Failed to create topic: {scored_topic.topic.title}")
                continue

            article_id = await self._create_article(
                topic_id, scored_topic.topic.title, auto_publish
            )
            if article_id:
                result.articles_generated += 1
                if auto_publish:
                    result.articles_published += 1
                else:
                    result.articles_queued += 1
                logger.info(
                    f"Generated article {article_id} for topic '{scored_topic.topic.title}' "
                    f"(intent_score={scored_topic.intent_score:.2f}, "
                    f"signals={scored_topic.intent_signals})"
                )
            else:
                result.errors.append(
                    f"Failed to generate article for topic: {scored_topic.topic.title}"
                )

        logger.info(
            f"Autopilot cycle complete for user {self.user_id[:8]}...: "
            f"discovered={result.topics_discovered}, generated={result.articles_generated}, "
            f"queued={result.articles_queued}, published={result.articles_published}"
        )

        return result


# =============================================================================
# Scheduled Job Functions
# =============================================================================


async def run_autopilot_for_user(
    user_id: str, workspace_id: str | None = None
) -> AutopilotCycleResult:
    """Run autopilot cycle for a single user.

    Args:
        user_id: User ID
        workspace_id: Optional workspace ID

    Returns:
        AutopilotCycleResult
    """
    service = SEOAutopilotService(user_id, workspace_id)
    return await service.run_scheduled_cycle()


async def run_autopilot_for_all_users() -> dict:
    """Run autopilot cycle for all users with autopilot enabled.

    Used by the scheduled job to process all enabled users.

    Returns:
        Dict with stats: users_processed, articles_generated, errors
    """
    stats = {
        "users_processed": 0,
        "articles_generated": 0,
        "articles_queued": 0,
        "articles_published": 0,
        "errors": 0,
        "tier_limits_reached": 0,
    }

    # Get all users with autopilot enabled
    with db_session() as session:
        result = session.execute(
            text("""
                SELECT user_id
                FROM user_context
                WHERE seo_autopilot_config->>'enabled' = 'true'
            """)
        )
        user_ids = [row[0] for row in result.fetchall()]

    logger.info(f"Running autopilot for {len(user_ids)} users")

    for user_id in user_ids:
        try:
            cycle_result = await run_autopilot_for_user(user_id)
            stats["users_processed"] += 1
            stats["articles_generated"] += cycle_result.articles_generated
            stats["articles_queued"] += cycle_result.articles_queued
            stats["articles_published"] += cycle_result.articles_published
            if cycle_result.tier_limit_reached:
                stats["tier_limits_reached"] += 1
            if cycle_result.errors:
                stats["errors"] += len(cycle_result.errors)
        except Exception as e:
            logger.error(f"Autopilot failed for user {user_id[:8]}...: {e}")
            stats["errors"] += 1

    logger.info(
        f"Autopilot batch complete: "
        f"users={stats['users_processed']}, articles={stats['articles_generated']}, "
        f"errors={stats['errors']}"
    )

    return stats
