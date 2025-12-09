"""Constants module for Board of One deliberation system.

This module centralizes magic numbers and thresholds used throughout the codebase,
making them easier to tune and maintain.

Organized by category:
- Graph Configuration: Round limits, recursion limits, timeouts
- LLM Configuration: Retry settings, token limits, model selection
- Embeddings Configuration: Voyage AI settings
- Circuit Breaker Configuration: Failure/recovery thresholds
- Rate Limiting: API rate limits by endpoint type
- Database Configuration: Connection pooling, Redis settings
- Cost Thresholds: Per-session cost limits by tier
- Similarity Thresholds: Various similarity comparisons
- Quality Metrics: Weights and thresholds for quality scoring
"""


class DeliberationPhases:
    """Phase definitions and round thresholds for deliberation progression."""

    EARLY_ROUNDS_MAX = 4
    """Maximum round number for early phase (1-4)"""

    MIDDLE_ROUNDS_MIN = 5
    """Start of middle phase"""

    MIDDLE_ROUNDS_MAX = 7
    """End of middle phase"""

    LATE_ROUNDS_MIN = 8
    """Start of late phase (8+)"""


class ThresholdValues:
    """Consensus and analysis thresholds for deliberation quality metrics."""

    CONVERGENCE_TARGET = 0.85
    """Target convergence score to consider consensus reached"""

    NOVELTY_THRESHOLD = 0.30
    """Maximum novelty score for convergence (below this = low new ideas)"""

    NOVELTY_LATE_ROUNDS_MAX = 0.30
    """Maximum novelty threshold for late rounds"""

    CONFLICT_DEADLOCK = 0.80
    """Conflict score indicating deadlock (high disagreement)"""

    AGREEMENT_KEYWORDS_RATIO = 0.15
    """Threshold for premature consensus detection (% of agreement keywords)"""

    SIMILARITY_THRESHOLD = 0.85
    """Minimum similarity score for detecting convergence"""


class ComplexityScores:
    """Problem complexity score ranges (1-10 scale)."""

    MIN = 1
    """Minimum valid complexity score"""

    MAX = 10
    """Maximum valid complexity score"""

    SIMPLE_MAX = 3
    """Maximum score for simple problems (1-3)"""

    MODERATE_MAX = 6
    """Maximum score for moderate problems (4-6)"""

    # Complex problems: 7-10 (by exclusion)


class Lengths:
    """Maximum counts for various deliberation components."""

    MAX_SUB_PROBLEMS = 5
    """Maximum number of sub-problems from decomposition"""

    MAX_DELIBERATION_ROUNDS = 15
    """Hard cap on deliberation rounds"""

    MIN_DELIBERATION_ROUNDS = 5
    """Minimum rounds for simple problems"""

    MODERATE_DELIBERATION_ROUNDS = 7
    """Target rounds for moderate complexity"""

    COMPLEX_DELIBERATION_ROUNDS = 10
    """Target rounds for complex problems"""


class TokenLimits:
    """Token limits for various LLM operations."""

    SUMMARY_TARGET = 100
    """Target token count for round summaries"""

    CONTRIBUTION_AVERAGE = 200
    """Average tokens per persona contribution"""

    RESPONSE_PREVIEW_LENGTH = 200
    """Characters to show in response previews (for logging)"""

    SNIPPET_MAX_LENGTH = 300
    """Maximum length for extracted snippets"""

    MAX_CONTRIBUTION_WORDS = 300
    """Maximum words per contribution (truncate/retry if exceeded)"""

    MIN_CONTRIBUTION_WORDS = 20
    """Minimum words for substantive contribution"""


class VotingThresholds:
    """Thresholds for voting and consensus detection."""

    UNANIMOUS_THRESHOLD = 0.95
    """Percentage for unanimous consensus (95%+)"""

    STRONG_MAJORITY_THRESHOLD = 0.75
    """Percentage for strong majority (75%+)"""

    SIMPLE_MAJORITY_THRESHOLD = 0.50
    """Percentage for simple majority (50%+)"""


# =============================================================================
# GRAPH CONFIGURATION
# =============================================================================


class GraphConfig:
    """Graph execution and round configuration."""

    MAX_ROUNDS_HARD_CAP = 6
    """Maximum rounds in parallel architecture"""

    EARLY_EXIT_MIN_ROUNDS = 2
    """Minimum rounds before early exit allowed"""

    CONVERGENCE_CHECK_MIN_ROUNDS = 2
    """Min rounds before convergence check"""

    RECENT_CONTRIBUTIONS_WINDOW = 6
    """Number of recent contributions to consider"""

    DELIBERATION_RECURSION_LIMIT = 250
    """Supports 5 sub-problems with overhead"""

    DEFAULT_TIMEOUT_SECONDS = 3600
    """1 hour default timeout"""

    CONVERGENCE_THRESHOLD = 0.90
    """Agreement threshold for convergence"""

    CONVERGENCE_THRESHOLD_LEGACY = 0.85
    """Previous threshold (for reference)"""

    MIN_PARTICIPATION_RATE = 0.70
    """Minimum participation for valid convergence"""

    MIN_NOVELTY_THRESHOLD = 0.40
    """Minimum novelty to continue deliberation"""

    EARLY_EXIT_CONVERGENCE_THRESHOLD = 0.85
    """High convergence triggers early exit"""

    EARLY_EXIT_NOVELTY_THRESHOLD = 0.30
    """Low novelty triggers early exit"""

    DEADLOCK_SIMILARITY_THRESHOLD = 0.75
    """Similarity indicating stuck debate"""

    DEADLOCK_REPETITION_RATE_THRESHOLD = 0.60
    """Repetition rate for deadlock"""


class SemanticSimilarity:
    """Semantic similarity thresholds for content comparison."""

    EXACT = 0.90
    """Nearly identical content"""

    PARAPHRASED = 0.85
    """Same idea, different words"""

    THEME = 0.80
    """Same general theme/topic"""


# =============================================================================
# LLM CONFIGURATION
# =============================================================================


class LLMConfig:
    """LLM retry and default parameter settings."""

    MAX_RETRIES = 3
    """Maximum retry attempts for LLM calls"""

    RETRY_BASE_DELAY = 0.2
    """Base delay in seconds (P2-005: reduced from 1.0s for faster error recovery)"""

    RETRY_MAX_DELAY = 60.0
    """Maximum delay in seconds"""

    DEFAULT_MAX_TOKENS = 4096
    """Default max output tokens"""

    DEFAULT_TEMPERATURE = 1.0
    """Default sampling temperature"""

    HAIKU_ROUNDS_THRESHOLD = 2
    """Use Haiku for early rounds (1-2)"""


# =============================================================================
# EMBEDDINGS CONFIGURATION (Voyage AI)
# =============================================================================


class EmbeddingsConfig:
    """Voyage AI embedding configuration."""

    MAX_RETRIES = 3
    """Max retries for embedding API"""

    INITIAL_DELAY = 0.5
    """Initial retry delay in seconds"""

    BACKOFF_FACTOR = 2.0
    """Exponential backoff multiplier"""

    REQUEST_TIMEOUT = 30.0
    """Request timeout in seconds"""

    SIMILARITY_THRESHOLD = 0.85
    """Default similarity threshold"""

    DIMENSIONS = 1024
    """Voyage-3 embedding dimensions"""


# =============================================================================
# CIRCUIT BREAKER CONFIGURATION
# =============================================================================


class CircuitBreakerConfig:
    """Circuit breaker thresholds for API resilience."""

    FAILURE_THRESHOLD = 5
    """Failures before circuit opens"""

    RECOVERY_TIMEOUT = 60
    """Seconds before testing recovery"""

    SUCCESS_THRESHOLD = 2
    """Successes to close circuit"""


# =============================================================================
# RATE LIMITING
# =============================================================================


class RateLimits:
    """API rate limits by endpoint type."""

    AUTH = "10/minute"
    """Auth endpoints (login, refresh)"""

    SESSION = "30/minute"
    """Session creation (IP-based, legacy)"""

    # Tiered session limits (user-based, prevents free tier abuse)
    SESSION_USER = "5/minute"
    """Session creation per user (default)"""

    SESSION_FREE = "5/minute"
    """Session creation for free tier users"""

    SESSION_PRO = "20/minute"
    """Session creation for pro tier users"""

    SESSION_ENTERPRISE = "100/minute"
    """Session creation for enterprise tier users"""

    STREAMING = "5/minute"
    """SSE streaming endpoints"""

    GENERAL = "60/minute"
    """General API endpoints"""

    CONTROL = "20/minute"
    """Control endpoints (start/kill deliberation)"""


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================


class DatabaseConfig:
    """PostgreSQL and Redis configuration."""

    POOL_MIN_CONNECTIONS = 1
    """Minimum connections in pool"""

    POOL_MAX_CONNECTIONS = 20
    """Maximum connections in pool"""

    REDIS_DEFAULT_PORT = 6379
    """Default Redis port"""

    REDIS_DEFAULT_DB = 0
    """Default Redis database number"""

    CHECKPOINT_TTL_SECONDS = 604800
    """7 days checkpoint retention"""

    # Redis TTLs - all use same duration to avoid mismatch
    REDIS_SESSION_TTL_SECONDS = 604800
    """7 days for session data (metadata, events, checkpoints)"""

    REDIS_METADATA_TTL_SECONDS = 604800
    """7 days for metadata (aligned with checkpoint TTL)"""

    REDIS_EVENTS_TTL_SECONDS = 604800
    """7 days for event history"""

    REDIS_CLEANUP_GRACE_PERIOD_SECONDS = 3600
    """1 hour grace period before cleanup (for reconnections)"""


class ResearchCacheConfig:
    """Research cache configuration."""

    SIMILARITY_THRESHOLD = 0.85
    """Similarity for cache hit"""

    QUERY_LIMIT = 10
    """Max results per cache query"""

    DEFAULT_FRESHNESS_DAYS = 90
    """Default freshness window"""

    STALE_THRESHOLD_DAYS = 30
    """Days before cache is stale"""

    HIT_SAVINGS_USD = 0.07
    """Estimated USD savings per hit"""


# =============================================================================
# COST THRESHOLDS (USD)
# =============================================================================


class CostThresholds:
    """Per-session cost limits by tier."""

    DEFAULT_MAX_PER_SESSION = 1.00
    """Default session cost limit"""

    TIER_FREE = 0.50
    """Free tier limit"""

    TIER_PRO = 2.00
    """Pro tier limit"""

    TIER_ENTERPRISE = 10.00
    """Enterprise tier limit"""

    TIER_LIMITS = {
        "free": TIER_FREE,
        "pro": TIER_PRO,
        "enterprise": TIER_ENTERPRISE,
    }


# =============================================================================
# QUALITY METRIC THRESHOLDS
# =============================================================================


class QualityMetrics:
    """Quality metric weights and thresholds."""

    FOCUS_CORE_THRESHOLD = 0.80
    """Core contribution relevance"""

    FOCUS_CONTEXT_THRESHOLD = 0.60
    """Context contribution relevance"""

    DRIFT_DETECTION_THRESHOLD = 0.60
    """Problem drift detection"""

    ON_TOPIC_OVERLAP_THRESHOLD = 0.20
    """Minimum overlap for on-topic"""

    # Meeting completeness weights (must sum to 1.0)
    COMPLETENESS_WEIGHT_EXPLORATION = 0.35
    COMPLETENESS_WEIGHT_CONVERGENCE = 0.35
    COMPLETENESS_WEIGHT_FOCUS = 0.20
    COMPLETENESS_WEIGHT_NOVELTY = 0.10


# =============================================================================
# CACHE TTL VALUES
# =============================================================================


class CacheTTL:
    """Cache time-to-live values in seconds."""

    LLM_CACHE = 86400
    """24 hours for LLM responses"""

    PERSONA_CACHE = 604800
    """7 days for persona selections"""

    PERSONA_SIMILARITY_THRESHOLD = 0.90
    """Similarity for persona cache hit"""

    LLM_SIMILARITY_THRESHOLD = 0.85
    """Similarity for LLM cache hit"""
