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

    # Persona selector model threshold
    HAIKU_SELECTOR_THRESHOLD = 6
    """Use Haiku for persona selection when complexity <= 6 (simple/moderate problems)"""


class DecompositionConfig:
    """Decomposition thresholds for complexity estimation.

    Used by decompose_node to estimate problem complexity based on
    word count and strategic keywords.
    """

    # Word count thresholds for initial complexity estimate
    WORD_THRESHOLD_SIMPLE = 20
    """Problems under 20 words → simple"""

    WORD_THRESHOLD_MODERATE = 50
    """Problems under 50 words → moderate"""

    WORD_THRESHOLD_COMPLEX = 100
    """Problems under 100 words → complex"""

    # Complexity score assignments (1-10 scale)
    COMPLEXITY_SIMPLE = 3
    """Initial complexity for simple problems (< 20 words)"""

    COMPLEXITY_MODERATE = 5
    """Initial complexity for moderate problems (< 50 words)"""

    COMPLEXITY_COMPLEX = 7
    """Initial complexity for complex problems (< 100 words)"""

    COMPLEXITY_VERY_COMPLEX = 8
    """Initial complexity for very complex problems (>= 100 words)"""

    # Keyword-based adjustments
    STRATEGIC_KEYWORD_BOOST = 2
    """Boost added when strategic keywords detected (pivot, acquisition, etc.)"""

    # Sub-problem limits (audit finding: avg was 4.2, capped to 4 for quality)
    MAX_SUBPROBLEMS_HARD_CAP = 4
    """Hard cap on sub-problems (quality > quantity)"""


class ModerationConfig:
    """Moderation and facilitation thresholds.

    Controls when moderator can intervene and recent contribution windows.
    """

    MIN_ROUNDS_BEFORE_VOTING = 2
    """Minimum rounds before voting allowed (parallel arch: 2 rounds = 6-10 contributions)"""

    RECENT_CONTRIBUTIONS_WINDOW = 3
    """Number of recent contributions to consider for moderator context"""


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

    MAX_CONTRIBUTION_WORDS = 200
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


class ContributionPruning:
    """Contribution pruning configuration for token optimization."""

    RETENTION_COUNT = 6
    """Number of contributions to retain after pruning (last 2 rounds worth)"""

    PRUNE_AFTER_PHASE = "convergence"
    """Phase after which pruning is applied (synthesis uses round_summaries)"""

    PRUNE_AFTER_ROUND_SUMMARY = True
    """Enable pruning at end of each round (after summary generated). Safe because summaries capture content."""

    ROUNDS_TO_RETAIN = 2
    """Number of recent rounds to retain raw contributions for (older rounds are summarized)"""


class PersonaContextConfig:
    """Persona context window configuration for token optimization.

    Controls how many recent contributions are included in persona prompts.
    Reducing this window saves ~3-5% token costs with minimal quality impact.
    """

    CONTRIBUTION_LIMIT = 3
    """Number of recent contributions to include in persona context.

    Reduced from 6 (2 rounds) to 3 (1 round) for cost optimization.
    Quality testing shows minimal degradation at this level since:
    - Round summaries provide broader context
    - Most recent round contributions are most relevant
    - Expert memory provides continuity
    """


class GraphConfig:
    """Graph execution and round configuration."""

    MAX_ROUNDS_DEFAULT = 6
    """Default max rounds for deliberation sessions (authoritative source)"""

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
    """LLM retry and default parameter settings.

    Note: For token budgets, prefer using bo1.config.TokenBudgets which provides
    semantic constants (SYNTHESIS, FACILITATOR, etc.) and env var override support.
    DEFAULT_MAX_TOKENS is kept here for backward compatibility.
    """

    MAX_RETRIES = 5
    """Maximum retry attempts for LLM calls (increased for transient API errors)"""

    RETRY_BASE_DELAY = 1.0
    """Base delay in seconds (increased to give APIs time to recover from overflow)"""

    RETRY_MAX_DELAY = 60.0
    """Maximum delay in seconds"""

    DEFAULT_MAX_TOKENS = 4096
    """Default max output tokens. Prefer TokenBudgets.DEFAULT for new code."""

    DEFAULT_TEMPERATURE = 0.85
    """Default sampling temperature (leaves headroom for phase adjustments)"""

    HAIKU_ROUNDS_THRESHOLD = 3
    """Use Haiku for early rounds (1-3)"""

    # Phase-adaptive temperature adjustments (delta applied to base temperature)
    # Maps to phases from get_round_phase_config(): initial, early, middle, late
    TEMPERATURE_ADJUSTMENTS: dict[str, float] = {
        "initial": 0.0,  # Round 1: baseline exploration
        "early": 0.15,  # Rounds 2-4 (~40%): +0.15 for divergent challenge
        "middle": 0.0,  # Rounds 5-7 (~70%): analytical, no adjustment
        "late": -0.10,  # Rounds 8+: -0.10 for convergent synthesis
    }
    """Temperature adjustments by deliberation phase"""

    TEMPERATURE_MIN = 0.0
    """Minimum clamped temperature"""

    TEMPERATURE_MAX = 1.0
    """Maximum clamped temperature (Anthropic API limit)"""


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

    BATCH_SIZE = 20
    """Number of texts to batch before API call (Voyage AI supports up to 128)"""

    BATCH_TIMEOUT_SECONDS = 60.0
    """Max wait time before flushing partial batch (high-traffic default)"""

    BATCH_TIMEOUT_HIGH_TRAFFIC = 60.0
    """Timeout during high traffic (>=0.5 RPS)"""

    BATCH_TIMEOUT_LOW_TRAFFIC = 10.0
    """Timeout during low traffic (<0.5 RPS) for faster response"""

    TRAFFIC_THRESHOLD_RPS = 0.5
    """Requests per second threshold for timeout selection"""

    TRAFFIC_WINDOW_SECONDS = 60.0
    """Window size for measuring traffic rate"""


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

    # Global IP-based flood protection (runs before all other limits)
    # Note: Admin endpoints (/api/admin/*) bypass this limit entirely
    # Normal user: ~20-30 calls/min; corporate NAT (10 users): 200-300 calls/min
    GLOBAL_IP = "180/minute"
    """Global per-IP limit to catch flood attacks (3/sec, allows corporate NAT)"""

    GLOBAL_IP_BURST = "50/second"
    """Short burst protection per IP"""

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

    STREAMING = "30/minute"
    """SSE streaming endpoints (allows reconnection during network issues)"""

    UPLOAD = "10/hour"
    """Dataset upload endpoint (prevents storage abuse)"""

    GENERAL = "60/minute"
    """General API endpoints"""

    CONTROL = "20/minute"
    """Control endpoints (start/kill deliberation)"""

    # Admin tier limits (much higher to allow dashboard page loads)
    # Single admin clicking through pages: ~50-100 calls/min with parallel requests
    ADMIN = "1200/minute"
    """Admin endpoints (dashboards fire multiple parallel requests on page load)"""

    # Public unauthenticated endpoints (CSRF-exempt, need extra protection)
    WAITLIST = "5/minute"
    """Waitlist signup endpoint (IP-based, prevents spam signups)"""

    # Authenticated user endpoints (added per rate limits audit)
    CONTEXT = "60/minute"
    """Business context CRUD operations"""

    USER = "60/minute"
    """User profile operations"""

    PROJECTS = "60/minute"
    """Project management operations"""

    MENTOR = "20/minute"
    """LLM-heavy mentor chat (expensive operations)"""

    BUSINESS_METRICS = "30/minute"
    """Business metrics endpoints"""

    COMPETITORS = "30/minute"
    """Competitor research endpoints"""

    ONBOARDING = "30/minute"
    """Onboarding flow endpoints"""

    TAGS = "60/minute"
    """Tag management operations"""

    BILLING = "30/minute"
    """Billing operations"""

    WORKSPACES = "60/minute"
    """Workspace management operations"""

    SEO_ANALYZE = "5/minute"
    """SEO trend analysis (expensive LLM+research operation)"""

    SEO_GENERATE = "2/minute"
    """SEO article generation (LLM-heavy operation)"""

    PEER_BENCHMARKS = "30/minute"
    """Peer benchmarking endpoints (consent toggle + data fetch)"""


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================


class DatabaseConfig:
    """PostgreSQL and Redis configuration."""

    POOL_MIN_CONNECTIONS = 1
    """Minimum connections in pool"""

    POOL_MAX_CONNECTIONS = 75
    """Maximum connections in pool"""

    POOL_POLLING_INTERVAL_MS = 100
    """Milliseconds between connection pool retry attempts"""

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


class SimilarityCacheThresholds:
    """Centralized similarity thresholds for all cache types.

    These values control cache hit detection:
    - Higher thresholds = stricter matching, fewer false positives
    - Lower thresholds = more permissive matching, higher hit rates
    """

    RESEARCH_CACHE = 0.85
    """Research cache hit threshold (flexibility for research variations)"""

    PERSONA_CACHE = 0.90
    """Persona selection cache (higher accuracy required)"""

    CONTRIBUTION_DEDUP = 0.80
    """Contribution deduplication (theme-level similarity)"""

    RESEARCH_DEDUP = 0.85
    """In-session research deduplication (match research cache)"""

    CONSOLIDATION = 0.75
    """Question consolidation/batching (broader grouping)"""

    # Additional thresholds from codebase audit
    DUPLICATE_CONTRIBUTION = 0.80
    """Duplicate contribution detection in rounds.py (theme-level)"""

    RESEARCH_DEPTH_TRIGGER = 0.75
    """Research depth semantic similarity trigger in research.py"""

    PROACTIVE_CONFIDENCE = 0.75
    """Proactive research detection confidence threshold in rounds.py"""


class ResearchCacheConfig:
    """Research cache configuration."""

    SIMILARITY_THRESHOLD = SimilarityCacheThresholds.RESEARCH_CACHE
    """Similarity for cache hit (references centralized threshold)"""

    QUERY_LIMIT = 10
    """Max results per cache query"""

    DEFAULT_FRESHNESS_DAYS = 90
    """Default freshness window"""

    STALE_THRESHOLD_DAYS = 30
    """Days before cache is stale"""

    HIT_SAVINGS_USD = 0.07
    """Estimated USD savings per hit"""

    CLEANUP_TTL_DAYS = 90
    """Days before cache entry eligible for cleanup (matches freshness)"""

    CLEANUP_ACCESS_GRACE_DAYS = 7
    """Don't delete if accessed within this many days"""


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


# =============================================================================
# AUTH LOCKOUT CONFIGURATION
# =============================================================================


class AuthLockout:
    """Auth lockout configuration for failed login attempts."""

    THRESHOLDS: dict[int, int] = {
        5: 30,  # 5 failures → 30 second lockout
        10: 300,  # 10 failures → 5 minute lockout
        15: 3600,  # 15 failures → 1 hour lockout
    }
    """Mapping of failure count to lockout duration in seconds"""

    WINDOW_SECONDS = 3600
    """Sliding window for counting failures (1 hour)"""

    KEY_PREFIX = "auth_lockout:"
    """Redis key prefix for lockout tracking"""


# =============================================================================
# SECURITY ALERTING CONFIGURATION
# =============================================================================


class SecurityAlerts:
    """Security event alerting thresholds and configuration."""

    # Auth failure alerting
    AUTH_FAILURE_THRESHOLD = 10
    """Number of auth failures before alert (per IP)"""

    AUTH_FAILURE_WINDOW_SECONDS = 300
    """5 minute sliding window for auth failures"""

    # Rate limit alerting
    RATE_LIMIT_THRESHOLD = 20
    """Number of rate limit hits before alert (per IP)"""

    RATE_LIMIT_WINDOW_SECONDS = 300
    """5 minute sliding window for rate limit hits"""

    # Lockout alerting
    LOCKOUT_THRESHOLD = 3
    """Number of lockouts before alert (per IP)"""

    LOCKOUT_WINDOW_SECONDS = 900
    """15 minute sliding window for lockouts"""

    # Alert deduplication
    ALERT_COOLDOWN_SECONDS = 900
    """15 minute cooldown between alerts for same IP/event"""

    # Redis key prefixes
    KEY_PREFIX = "security_event:"
    """Redis key prefix for event tracking"""

    ALERT_DEDUP_PREFIX = "security_alert_sent:"
    """Redis key prefix for alert deduplication"""


# =============================================================================
# RATE LIMITER HEALTH MONITORING
# =============================================================================


class RateLimiterHealth:
    """Rate limiter Redis health monitoring configuration."""

    FAILURE_THRESHOLD = 3
    """Consecutive failures before alerting"""

    ALERT_COOLDOWN_SECONDS = 900
    """15 minute deduplication window for alerts"""

    HEALTH_CHECK_INTERVAL_SECONDS = 30
    """Interval for periodic health checks when degraded"""

    KEY_PREFIX = "rate_limiter_health:"
    """Redis key prefix for health tracking"""

    ALERT_DEDUP_KEY = "rate_limiter_alert_sent"
    """Redis key for alert deduplication"""


# =============================================================================
# HEALTH CHECK THRESHOLDS
# =============================================================================


class HealthThresholds:
    """Health check thresholds for operational monitoring."""

    # Event queue depth thresholds
    EVENT_QUEUE_WARNING = 50
    """Warning threshold for event queue depth"""

    EVENT_QUEUE_CRITICAL = 100
    """Critical threshold for event queue depth"""

    # Circuit breaker health
    CIRCUIT_BREAKER_HEALTHY_STATES = ["closed", "half_open"]
    """States considered healthy for circuit breakers"""


# =============================================================================
# GANTT COLOR CODING
# =============================================================================


class GanttColorStrategy:
    """Gantt chart color coding strategies."""

    BY_STATUS = "BY_STATUS"
    """Color by action status"""

    BY_PROJECT = "BY_PROJECT"
    """Color by project"""

    BY_PRIORITY = "BY_PRIORITY"
    """Color by action priority"""

    HYBRID = "HYBRID"
    """Hybrid: status primary + project accent stripe"""

    DEFAULT = BY_STATUS
    """Default strategy for new users"""

    ALL = [BY_STATUS, BY_PROJECT, BY_PRIORITY, HYBRID]
    """All available strategies"""


class GanttStatusColors:
    """Hex color codes for action statuses."""

    NOT_STARTED = "#9CA3AF"  # gray-400
    """Not started: gray"""

    IN_PROGRESS = "#3B82F6"  # blue-500
    """In progress: blue"""

    BLOCKED = "#EF4444"  # red-500
    """Blocked: red"""

    ON_HOLD = "#F59E0B"  # amber-500
    """On hold: amber"""

    COMPLETE = "#10B981"  # emerald-500
    """Complete: green"""

    CANCELLED = "#6B7280"  # gray-500 (with strikethrough in UI)
    """Cancelled: gray"""

    MAP = {
        "not_started": NOT_STARTED,
        "in_progress": IN_PROGRESS,
        "blocked": BLOCKED,
        "on_hold": ON_HOLD,
        "complete": COMPLETE,
        "cancelled": CANCELLED,
    }


class GanttPriorityColors:
    """Hex color codes for action priorities."""

    LOW = "#10B981"  # emerald-500
    """Low priority: green"""

    MEDIUM = "#F59E0B"  # amber-500
    """Medium priority: amber"""

    HIGH = "#EF4444"  # red-500
    """High priority: red"""

    MAP = {
        "low": LOW,
        "medium": MEDIUM,
        "high": HIGH,
    }


class GanttProjectColors:
    """Rotating HSL color palette for projects (up to 20 unique projects)."""

    PALETTE = [
        "#8B5CF6",  # violet-500
        "#EC4899",  # pink-500
        "#06B6D4",  # cyan-500
        "#6366F1",  # indigo-500
        "#14B8A6",  # teal-500
        "#F97316",  # orange-500
        "#84CC16",  # lime-500
        "#0EA5E9",  # sky-500
        "#A855F7",  # purple-500
        "#06B6D4",  # cyan-500 (rotate)
        "#059669",  # emerald-600
        "#7C3AED",  # violet-600
        "#DC2626",  # red-600
        "#2563EB",  # blue-600
        "#16A34A",  # green-600
        "#EA580C",  # orange-600
        "#7C3AED",  # purple-600 (rotate)
        "#0369A1",  # sky-700
        "#BE185D",  # pink-700
        "#6B21A8",  # purple-900
    ]

    @staticmethod
    def get_color_for_project(project_index: int) -> str:
        """Get color for a project by rotating through the palette.

        Args:
            project_index: 0-based project index

        Returns:
            Hex color string
        """
        return GanttProjectColors.PALETTE[project_index % len(GanttProjectColors.PALETTE)]


class GanttColorCache:
    """Gantt color cache configuration."""

    TTL_SECONDS = 600  # 10 minutes
    """Cache TTL for computed colors"""

    KEY_PREFIX = "gantt_color:"
    """Redis key prefix for color cache"""


# =============================================================================
# INDUSTRY BENCHMARK CONFIGURATION
# =============================================================================


class BenchmarkCategories:
    """Benchmark metric categories."""

    GROWTH = "growth"
    """Growth metrics: MRR, revenue, expansion"""

    RETENTION = "retention"
    """Retention metrics: churn, NRR, LTV"""

    EFFICIENCY = "efficiency"
    """Efficiency metrics: CAC payback, LTV:CAC, burn multiple"""

    ENGAGEMENT = "engagement"
    """Engagement metrics: DAU/MAU, activation, NPS"""

    ALL = [GROWTH, RETENTION, EFFICIENCY, ENGAGEMENT]


class IndustrySegments:
    """Industry segments for benchmark filtering."""

    SAAS = "SaaS"
    ECOMMERCE = "E-commerce"
    FINTECH = "Fintech"
    HEALTHCARE = "Healthcare"
    MARKETPLACE = "Marketplace"

    ALL = [SAAS, ECOMMERCE, FINTECH, HEALTHCARE, MARKETPLACE]


class SessionManagerConfig:
    """Session manager capacity and eviction configuration."""

    MAX_CONCURRENT_SESSIONS = 50
    """Maximum number of concurrent active sessions"""

    EVICTION_GRACE_PERIOD_SECONDS = 30
    """Seconds to wait before hard-kill on eviction"""


# =============================================================================
# PARTITION RETENTION CONFIGURATION
# =============================================================================


class PartitionRetention:
    """Per-table retention periods for partitioned tables (in days)."""

    API_COSTS = 90
    """90 days retention for api_costs (high-volume cost tracking)"""

    SESSION_EVENTS = 180
    """180 days retention for session_events (event replay/debugging)"""

    CONTRIBUTIONS = 365
    """365 days retention for contributions (deliberation history)"""

    TABLE_RETENTION = {
        "api_costs": API_COSTS,
        "session_events": SESSION_EVENTS,
        "contributions": CONTRIBUTIONS,
    }

    @staticmethod
    def get_retention_days(table: str) -> int:
        """Get retention period in days for a partitioned table.

        Args:
            table: Table name (api_costs, session_events, contributions)

        Returns:
            Retention period in days (defaults to 365 if table unknown)
        """
        return PartitionRetention.TABLE_RETENTION.get(table, 365)


class MetricLabelConfig:
    """Prometheus metric label configuration for cardinality control."""

    LABEL_TRUNCATE_LENGTH = 8
    """Default truncation length for high-cardinality labels (session_id, user_id)."""


class RedisReconnection:
    """Redis reconnection strategy configuration."""

    INITIAL_DELAY_MS = 1000
    """Initial retry delay in milliseconds (1 second)"""

    MAX_DELAY_MS = 30000
    """Maximum retry delay in milliseconds (30 seconds)"""

    MAX_ATTEMPTS = 10
    """Maximum reconnection attempts before giving up"""

    BUFFER_MAX_EVENTS = 100
    """Maximum events to buffer during disconnection"""

    BACKOFF_FACTOR = 2.0
    """Exponential backoff multiplier"""


class RetryConfig:
    """Database retry configuration.

    Timeout Guidance:
        Always specify `total_timeout` explicitly on @retry_db decorators.
        Recommended values by operation type:
        - User-facing writes: 30.0 (default) - interactive response times
        - Background batch: 60.0 - more tolerance for transient failures
        - Health checks: 5.0 - fast failure for monitoring
    """

    MAX_ATTEMPTS = 3
    """Maximum retry attempts"""

    BASE_DELAY = 0.5
    """Initial delay in seconds"""

    MAX_DELAY = 10.0
    """Maximum delay between retries in seconds"""

    TOTAL_TIMEOUT = 30.0
    """Total timeout across all retries (max_attempts * max_delay worst case)"""

    # Named constants for common timeout scenarios
    TIMEOUT_USER_FACING = 30.0
    """User-facing operations (default)"""

    TIMEOUT_BATCH = 60.0
    """Background batch operations"""

    TIMEOUT_HEALTH = 5.0
    """Health checks and monitoring"""


class UsageMetrics:
    """Usage metric names and Redis key configuration."""

    # Metric names
    MEETINGS_CREATED = "meetings_created"
    DATASETS_UPLOADED = "datasets_uploaded"
    MENTOR_CHATS = "mentor_chats"
    API_CALLS = "api_calls"

    # All tracked metrics
    ALL = [MEETINGS_CREATED, DATASETS_UPLOADED, MENTOR_CHATS, API_CALLS]

    # Redis key patterns
    KEY_PREFIX = "usage:"
    DAILY_KEY_PATTERN = "{prefix}{user_id}:{metric}:daily:{date}"
    MONTHLY_KEY_PATTERN = "{prefix}{user_id}:{metric}:monthly:{year_month}"

    # TTL values (seconds)
    DAILY_TTL = 86400 * 2  # 2 days (buffer for timezone edge cases)
    MONTHLY_TTL = 86400 * 35  # 35 days (buffer for month rollover)


class BetaMeetingCap:
    """Beta meeting cap configuration (rolling window rate limiting)."""

    MAX_MEETINGS = 4
    """Maximum meetings allowed per rolling window"""

    WINDOW_HOURS = 24
    """Rolling window in hours"""

    @staticmethod
    def is_enabled() -> bool:
        """Check if beta meeting cap is enabled via env."""
        import os

        return os.getenv("BETA_MEETING_CAP_ENABLED", "true").lower() == "true"


class UserContextCache:
    """User context Redis cache configuration."""

    TTL_SECONDS = 300
    """Cache TTL in seconds (5 minutes)"""

    KEY_PREFIX = "user_context:"
    """Redis key prefix for user context"""

    @staticmethod
    def is_enabled() -> bool:
        """Check if user context caching is enabled via env."""
        import os

        return os.getenv("USER_CONTEXT_CACHE_ENABLED", "true").lower() == "true"


class ChallengePhaseConfig:
    """Challenge phase validation configuration."""

    ROUNDS = [3, 4]
    """1-indexed rounds requiring challenge validation (challenge phase)"""

    AGREEMENT_THRESHOLD = 0.6
    """If >60% of content is agreement without challenge, reject (reserved for future use)"""


class PoolDegradationConfig:
    """Database pool graceful degradation configuration."""

    DEGRADATION_THRESHOLD_PCT = 90
    """Pool utilization % to enter degradation mode (start queuing)"""

    QUEUE_MAX_SIZE = 50
    """Maximum pending requests in degradation queue"""

    QUEUE_TIMEOUT_SECONDS = 10.0
    """Maximum time to wait in queue before 503"""

    SHED_LOAD_THRESHOLD_PCT = 95
    """Pool utilization % to start rejecting writes"""

    RETRY_AFTER_BASE_SECONDS = 5
    """Base Retry-After header value in seconds"""

    RETRY_AFTER_JITTER_SECONDS = 3
    """Random jitter to add to Retry-After (prevents thundering herd)"""


class OutputLengthConfig:
    """LLM output length validation configuration."""

    VERBOSE_THRESHOLD = 0.5
    """Warn if output uses <50% of max_tokens (response may be too brief)"""

    TRUNCATION_THRESHOLD = 0.9
    """Warn if output uses >90% of max_tokens (response may be truncated)"""

    @staticmethod
    def is_enabled() -> bool:
        """Check if output length validation is enabled via env var."""
        import os

        return os.getenv("OUTPUT_LENGTH_VALIDATION_ENABLED", "true").lower() == "true"


class LLMRateLimiterConfig:
    """LLM rate limiter configuration for session-level call throttling.

    Prevents runaway sessions from consuming excessive resources.
    """

    MAX_ROUNDS_PER_SESSION = 10
    """Maximum rounds per session (hard cap)"""

    MAX_CALLS_PER_MINUTE = 6
    """Maximum LLM calls per minute per session (sliding window)"""

    WINDOW_SECONDS = 60
    """Sliding window size in seconds for call rate limiting"""

    CLEANUP_MULTIPLIER = 2
    """Cleanup stale entries after WINDOW_SECONDS * CLEANUP_MULTIPLIER"""

    @staticmethod
    def is_enabled() -> bool:
        """Check if LLM rate limiter is enabled via env var."""
        import os

        return os.getenv("LLM_RATE_LIMITER_ENABLED", "true").lower() == "true"


class StatementTimeoutConfig:
    """Database statement timeout configuration.

    Prevents runaway queries from blocking connections indefinitely.
    Uses PostgreSQL's statement_timeout setting (per-transaction via SET LOCAL).
    """

    DEFAULT_TIMEOUT_MS = 30000
    """Default timeout for batch operations (30 seconds)"""

    INTERACTIVE_TIMEOUT_MS = 5000
    """Timeout for user-facing/interactive queries (5 seconds)"""

    @staticmethod
    def get_default_timeout() -> int:
        """Get default timeout from env or constant."""
        import os

        return int(
            os.getenv("DB_STATEMENT_TIMEOUT_MS", str(StatementTimeoutConfig.DEFAULT_TIMEOUT_MS))
        )

    @staticmethod
    def get_interactive_timeout() -> int:
        """Get interactive timeout from env or constant."""
        import os

        return int(
            os.getenv(
                "DB_INTERACTIVE_TIMEOUT_MS", str(StatementTimeoutConfig.INTERACTIVE_TIMEOUT_MS)
            )
        )


class ModelSelectionConfig:
    """Model selection and A/B testing configuration.

    Controls which model tier is used for different rounds:
    - HAIKU_ROUND_LIMIT: Default round limit for using fast tier (default: 3)
    - When A/B testing enabled, sessions are randomly assigned to test/control groups
    """

    HAIKU_ROUND_LIMIT = 3
    """Default round limit for using fast tier (rounds 1-3 use Haiku)"""

    AB_TEST_LIMIT = 4
    """Test group round limit - extends fast tier to round 4"""

    AB_TEST_PERCENTAGE = 50
    """Percentage of sessions assigned to test group (0-100)"""

    @staticmethod
    def get_haiku_round_limit() -> int:
        """Get haiku round limit from env or default."""
        import os

        return int(os.getenv("HAIKU_ROUND_LIMIT", str(ModelSelectionConfig.HAIKU_ROUND_LIMIT)))

    @staticmethod
    def is_ab_test_enabled() -> bool:
        """Check if A/B testing is enabled via env var."""
        import os

        return os.getenv("HAIKU_AB_TEST_ENABLED", "false").lower() == "true"

    @staticmethod
    def get_ab_test_limit() -> int:
        """Get A/B test round limit from env or default."""
        import os

        return int(os.getenv("HAIKU_AB_TEST_LIMIT", str(ModelSelectionConfig.AB_TEST_LIMIT)))

    @staticmethod
    def get_ab_test_percentage() -> int:
        """Get A/B test percentage from env or default."""
        import os

        return int(
            os.getenv("HAIKU_AB_TEST_PERCENTAGE", str(ModelSelectionConfig.AB_TEST_PERCENTAGE))
        )

    @staticmethod
    def get_ab_group(session_id: str | None) -> str:
        """Determine A/B test group for a session.

        Uses deterministic hash of session_id to ensure consistent group assignment.

        Args:
            session_id: Session identifier (if None, returns "none")

        Returns:
            "test", "control", or "none" (if A/B test disabled or no session_id)
        """
        if not ModelSelectionConfig.is_ab_test_enabled() or not session_id:
            return "none"

        # Deterministic hash-based assignment
        import hashlib

        hash_value = int(hashlib.sha256(session_id.encode()).hexdigest(), 16)
        percentage = hash_value % 100

        if percentage < ModelSelectionConfig.get_ab_test_percentage():
            return "test"
        return "control"


class ActionValidationLimits:
    """Validation limits for action text fields.

    Prevents DB overflow and DoS via oversized payloads.
    """

    MAX_BLOCKING_REASON_LENGTH = 2000
    """Maximum length for blocking_reason and cancellation_reason fields"""

    MAX_STEP_LENGTH = 1000
    """Maximum length for what_and_how items"""

    MAX_CRITERION_LENGTH = 500
    """Maximum length for success_criteria and kill_criteria items"""

    MAX_LIST_ITEMS = 20
    """Maximum items in what_and_how, success_criteria, kill_criteria lists"""


class CostAnomalyConfig:
    """Cost anomaly detection configuration.

    Tracks unusual cost patterns that may indicate issues:
    - high_single_call: Single API call exceeds threshold (runaway prompt)
    - high_session_total: Session total exceeds threshold (stuck loop)
    - negative_cost: Negative cost detected (data corruption)
    """

    SINGLE_CALL_THRESHOLD_USD = 0.50
    """Alert if single LLM call costs more than this (default $0.50)"""

    SESSION_TOTAL_THRESHOLD_USD = 5.00
    """Alert if session total exceeds this (default $5.00)"""

    @staticmethod
    def get_single_call_threshold() -> float:
        """Get single call threshold from env or default."""
        import os

        return float(os.getenv("COST_ANOMALY_SINGLE_CALL_THRESHOLD", "0.50"))

    @staticmethod
    def get_session_total_threshold() -> float:
        """Get session total threshold from env or default."""
        import os

        return float(os.getenv("COST_ANOMALY_SESSION_TOTAL_THRESHOLD", "5.00"))

    @staticmethod
    def is_enabled() -> bool:
        """Check if cost anomaly detection is enabled via env var."""
        import os

        return os.getenv("COST_ANOMALY_DETECTION_ENABLED", "true").lower() == "true"

    @staticmethod
    def are_alerts_enabled() -> bool:
        """Check if cost anomaly ntfy alerts are enabled.

        Allows disabling ntfy alerts while keeping Prometheus metrics.
        Default: true (alerts enabled when anomaly detection is enabled)
        """
        import os

        return os.getenv("COST_ANOMALY_ALERTS_ENABLED", "true").lower() == "true"
