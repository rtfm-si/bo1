"""Peer benchmarking service.

Enables anonymous comparison of user metrics against industry peers.
- Consent management (opt-in/opt-out)
- Aggregation with k-anonymity protection (min 5 peers)
- Percentile calculation for industry-level metrics

Privacy-first: no PII, industry-level only, explicit consent required.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Minimum number of contributors required for k-anonymity
K_ANONYMITY_THRESHOLD = 5

# Metrics available for peer benchmarking (subset of BENCHMARK_FIELDS)
PEER_BENCHMARK_METRICS = [
    "revenue",
    "customers",
    "growth_rate",
    "team_size",
    "mau_bucket",
    "dau_mau_ratio",
    "arpu",
    "arr_growth_rate",
    "grr",
    "active_churn",
    "revenue_churn",
    "nps",
    "quick_ratio",
    "traffic_range",
    "revenue_stage",
]

# Human-friendly display names
METRIC_DISPLAY_NAMES = {
    "revenue": "Monthly Revenue",
    "customers": "Customer Count",
    "growth_rate": "Growth Rate",
    "team_size": "Team Size",
    "mau_bucket": "Monthly Active Users",
    "dau_mau_ratio": "DAU/MAU Ratio",
    "arpu": "Average Revenue Per User",
    "arr_growth_rate": "ARR Growth Rate",
    "grr": "Gross Revenue Retention",
    "active_churn": "Customer Churn Rate",
    "revenue_churn": "Revenue Churn Rate",
    "nps": "Net Promoter Score",
    "quick_ratio": "SaaS Quick Ratio",
    "traffic_range": "Website Traffic",
    "revenue_stage": "Revenue Stage",
}


@dataclass
class ConsentStatus:
    """User's peer benchmark consent status."""

    consented: bool
    consented_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass
class PeerPercentile:
    """Percentile data for a single metric."""

    metric: str
    display_name: str
    p10: float | None
    p25: float | None
    p50: float | None
    p75: float | None
    p90: float | None
    sample_count: int
    user_value: float | None = None
    user_percentile: float | None = None


@dataclass
class PeerBenchmarkResult:
    """Result of peer benchmark comparison."""

    industry: str
    metrics: list[PeerPercentile]
    updated_at: datetime | None = None


# =============================================================================
# Consent Management
# =============================================================================


def get_consent_status(user_id: str) -> ConsentStatus:
    """Get user's current peer benchmark consent status.

    Args:
        user_id: User identifier

    Returns:
        ConsentStatus with current state
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT consented_at, revoked_at
                FROM peer_benchmark_consent
                WHERE user_id = %s
                """,
                (user_id,),
            )
            result = cur.fetchone()

            if not result:
                return ConsentStatus(consented=False)

            consented_at = result["consented_at"]
            revoked_at = result["revoked_at"]
            # User is consented if they have a consent timestamp and haven't revoked
            is_consented = consented_at is not None and revoked_at is None

            return ConsentStatus(
                consented=is_consented,
                consented_at=consented_at,
                revoked_at=revoked_at,
            )


def give_consent(user_id: str) -> ConsentStatus:
    """Opt-in user to peer benchmarking.

    Args:
        user_id: User identifier

    Returns:
        Updated ConsentStatus
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            now = datetime.now(UTC)

            # Upsert: insert or update existing record
            cur.execute(
                """
                INSERT INTO peer_benchmark_consent (user_id, consented_at, revoked_at)
                VALUES (%s, %s, NULL)
                ON CONFLICT (user_id)
                DO UPDATE SET consented_at = %s, revoked_at = NULL
                """,
                (user_id, now, now),
            )
            conn.commit()

            logger.info("peer_benchmark_consent_given", extra={"user_id": user_id})
            return ConsentStatus(consented=True, consented_at=now)


def revoke_consent(user_id: str) -> ConsentStatus:
    """Opt-out user from peer benchmarking.

    Immediate effect: user's data excluded from future aggregations.

    Args:
        user_id: User identifier

    Returns:
        Updated ConsentStatus
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            now = datetime.now(UTC)

            cur.execute(
                """
                UPDATE peer_benchmark_consent
                SET revoked_at = %s
                WHERE user_id = %s
                RETURNING consented_at
                """,
                (now, user_id),
            )
            result = cur.fetchone()
            conn.commit()

            if result:
                logger.info("peer_benchmark_consent_revoked", extra={"user_id": user_id})
                return ConsentStatus(
                    consented=False,
                    consented_at=result["consented_at"],
                    revoked_at=now,
                )

            return ConsentStatus(consented=False)


def is_consented(user_id: str) -> bool:
    """Quick check if user has consented to peer benchmarking.

    Args:
        user_id: User identifier

    Returns:
        True if user has active consent
    """
    return get_consent_status(user_id).consented


# =============================================================================
# Aggregation
# =============================================================================


def get_contributing_users(industry: str) -> list[str]:
    """Get user IDs with active consent for an industry.

    Args:
        industry: Industry segment to filter by

    Returns:
        List of user IDs eligible for aggregation
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pbc.user_id
                FROM peer_benchmark_consent pbc
                JOIN user_context uc ON pbc.user_id = uc.user_id
                WHERE pbc.revoked_at IS NULL
                AND uc.industry = %s
                """,
                (industry,),
            )
            result = cur.fetchall()

            return [row["user_id"] for row in result]


def _parse_numeric_value(value: Any) -> float | None:
    """Parse a benchmark value to float.

    Handles various formats: "50000", "$50K", "15%", "1.5M", etc.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        return None

    # Clean the string
    clean = value.strip().upper()

    # Remove common prefixes/suffixes
    clean = clean.replace("$", "").replace("%", "").replace(",", "")

    # Handle K/M/B suffixes
    multiplier = 1
    if clean.endswith("K"):
        multiplier = 1_000
        clean = clean[:-1]
    elif clean.endswith("M"):
        multiplier = 1_000_000
        clean = clean[:-1]
    elif clean.endswith("B"):
        multiplier = 1_000_000_000
        clean = clean[:-1]

    try:
        return float(clean) * multiplier
    except ValueError:
        return None


def aggregate_industry_metrics(industry: str) -> dict[str, PeerPercentile]:
    """Compute percentiles for all metrics in an industry.

    Enforces k-anonymity: metrics with <5 contributors return None percentiles.

    Args:
        industry: Industry segment to aggregate

    Returns:
        Dict of metric_name -> PeerPercentile
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get all consented users' metrics for this industry
            cur.execute(
                """
                SELECT
                    uc.revenue, uc.customers, uc.growth_rate, uc.team_size,
                    uc.mau_bucket, uc.traffic_range, uc.revenue_stage,
                    uc.dau, uc.mau,
                    CASE WHEN uc.mau > 0 THEN uc.dau::float / uc.mau ELSE NULL END as dau_mau_ratio,
                    uc.arpu, uc.arr_growth_rate, uc.grr,
                    uc.active_churn, uc.revenue_churn, uc.nps, uc.quick_ratio
                FROM user_context uc
                JOIN peer_benchmark_consent pbc ON uc.user_id = pbc.user_id
                WHERE pbc.revoked_at IS NULL
                AND uc.industry = %s
                """,
                (industry,),
            )
            result = cur.fetchall()

            if not result:
                return {}

            # Collect values per metric
            metric_values: dict[str, list[float]] = {
                metric: [] for metric in PEER_BENCHMARK_METRICS
            }

            for row in result:
                # Map row to metrics
                row_dict = {
                    "revenue": row["revenue"],
                    "customers": row["customers"],
                    "growth_rate": row["growth_rate"],
                    "team_size": row["team_size"],
                    "mau_bucket": row["mau_bucket"],
                    "traffic_range": row["traffic_range"],
                    "revenue_stage": row["revenue_stage"],
                    "dau_mau_ratio": row["dau_mau_ratio"],
                    "arpu": row["arpu"],
                    "arr_growth_rate": row["arr_growth_rate"],
                    "grr": row["grr"],
                    "active_churn": row["active_churn"],
                    "revenue_churn": row["revenue_churn"],
                    "nps": row["nps"],
                    "quick_ratio": row["quick_ratio"],
                }

                for metric in PEER_BENCHMARK_METRICS:
                    val = _parse_numeric_value(row_dict.get(metric))
                    if val is not None:
                        metric_values[metric].append(val)

            # Compute percentiles per metric
            percentiles: dict[str, PeerPercentile] = {}
            now = datetime.now(UTC)

            for metric, values in metric_values.items():
                sample_count = len(values)

                if sample_count < K_ANONYMITY_THRESHOLD:
                    # Not enough data for k-anonymity
                    percentiles[metric] = PeerPercentile(
                        metric=metric,
                        display_name=METRIC_DISPLAY_NAMES.get(metric, metric),
                        p10=None,
                        p25=None,
                        p50=None,
                        p75=None,
                        p90=None,
                        sample_count=sample_count,
                    )
                else:
                    # Compute percentiles
                    sorted_vals = sorted(values)
                    n = len(sorted_vals)

                    def percentile(
                        p: float, _vals: list[float] = sorted_vals, _n: int = n
                    ) -> float:
                        idx = (_n - 1) * p
                        lower = int(idx)
                        upper = min(lower + 1, _n - 1)
                        weight = idx - lower
                        return _vals[lower] * (1 - weight) + _vals[upper] * weight

                    percentiles[metric] = PeerPercentile(
                        metric=metric,
                        display_name=METRIC_DISPLAY_NAMES.get(metric, metric),
                        p10=percentile(0.10),
                        p25=percentile(0.25),
                        p50=percentile(0.50),
                        p75=percentile(0.75),
                        p90=percentile(0.90),
                        sample_count=sample_count,
                    )

            # Update cached aggregates
            _update_aggregate_cache(industry, percentiles, now)

            return percentiles


def _update_aggregate_cache(
    industry: str, percentiles: dict[str, PeerPercentile], updated_at: datetime
) -> None:
    """Update cached aggregate data in database.

    Args:
        industry: Industry segment
        percentiles: Computed percentiles
        updated_at: Timestamp for cache
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            for metric, data in percentiles.items():
                cur.execute(
                    """
                    INSERT INTO peer_benchmark_aggregates
                        (industry, metric_name, p10, p25, p50, p75, p90, sample_count, updated_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (industry, metric_name)
                    DO UPDATE SET
                        p10 = EXCLUDED.p10, p25 = EXCLUDED.p25, p50 = EXCLUDED.p50,
                        p75 = EXCLUDED.p75, p90 = EXCLUDED.p90,
                        sample_count = EXCLUDED.sample_count, updated_at = EXCLUDED.updated_at
                    """,
                    (
                        industry,
                        metric,
                        data.p10,
                        data.p25,
                        data.p50,
                        data.p75,
                        data.p90,
                        data.sample_count,
                        updated_at,
                    ),
                )
            conn.commit()


def get_cached_aggregates(industry: str) -> dict[str, PeerPercentile] | None:
    """Get cached aggregate data for an industry.

    Args:
        industry: Industry segment

    Returns:
        Dict of metric_name -> PeerPercentile, or None if no cache
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric_name, p10, p25, p50, p75, p90, sample_count, updated_at
                FROM peer_benchmark_aggregates
                WHERE industry = %s
                """,
                (industry,),
            )
            result = cur.fetchall()

            if not result:
                return None

            percentiles: dict[str, PeerPercentile] = {}
            for row in result:
                metric = row["metric_name"]
                percentiles[metric] = PeerPercentile(
                    metric=metric,
                    display_name=METRIC_DISPLAY_NAMES.get(metric, metric),
                    p10=row["p10"],
                    p25=row["p25"],
                    p50=row["p50"],
                    p75=row["p75"],
                    p90=row["p90"],
                    sample_count=row["sample_count"],
                )

            return percentiles


# =============================================================================
# User Comparison
# =============================================================================


def get_user_percentile_rank(
    user_id: str, industry: str, metric: str, user_value: float
) -> float | None:
    """Calculate user's percentile rank for a metric.

    Args:
        user_id: User identifier
        industry: Industry segment
        metric: Metric name
        user_value: User's value for this metric

    Returns:
        Percentile rank (0-100), or None if insufficient data
    """
    # Validate metric name to prevent SQL injection
    if metric not in PEER_BENCHMARK_METRICS:
        return None

    with db_session() as conn:
        with conn.cursor() as cur:
            # Get all values for this metric from consented users
            # Using format() here is safe because metric is validated against whitelist
            cur.execute(
                f"""
                SELECT uc.{metric}
                FROM user_context uc
                JOIN peer_benchmark_consent pbc ON uc.user_id = pbc.user_id
                WHERE pbc.revoked_at IS NULL
                AND uc.industry = %s
                AND uc.{metric} IS NOT NULL
                """,  # noqa: S608
                (industry,),
            )
            result = cur.fetchall()

            if len(result) < K_ANONYMITY_THRESHOLD:
                return None

            # Parse all values
            values = []
            for row in result:
                val = _parse_numeric_value(row[metric])
                if val is not None:
                    values.append(val)

            if len(values) < K_ANONYMITY_THRESHOLD:
                return None

            # Calculate percentile rank
            count_below = sum(1 for v in values if v < user_value)
            percentile = (count_below / len(values)) * 100

            return round(percentile, 1)


def get_preview_metric(user_id: str) -> dict | None:
    """Get a single preview metric for non-opted users.

    Returns the first metric with sufficient sample count (>=5 peers)
    showing only industry median. No user-specific data included.

    Args:
        user_id: User identifier (to get their industry)

    Returns:
        Dict with metric, display_name, industry, p50, sample_count or None
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get user's industry
            cur.execute(
                "SELECT industry FROM user_context WHERE user_id = %s",
                (user_id,),
            )
            result = cur.fetchone()

            if not result or not result["industry"]:
                return None

            industry = result["industry"]

    # Get cached aggregates for this industry
    aggregates = get_cached_aggregates(industry)
    if not aggregates:
        # Compute fresh if no cache exists
        aggregates = aggregate_industry_metrics(industry)

    if not aggregates:
        return None

    # Find first metric with sufficient data
    for _metric, data in aggregates.items():
        if data.sample_count >= K_ANONYMITY_THRESHOLD and data.p50 is not None:
            return {
                "metric": data.metric,
                "display_name": data.display_name,
                "industry": industry,
                "p50": data.p50,
                "sample_count": data.sample_count,
            }

    return None


def get_peer_comparison(user_id: str) -> PeerBenchmarkResult | None:
    """Get full peer comparison for a user.

    Args:
        user_id: User identifier

    Returns:
        PeerBenchmarkResult with industry percentiles and user rankings, or None
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get user's industry
            cur.execute(
                "SELECT industry FROM user_context WHERE user_id = %s",
                (user_id,),
            )
            result = cur.fetchone()

            if not result or not result["industry"]:
                return None

            industry = result["industry"]

            # Get user's benchmark values
            cur.execute(
                """
                SELECT
                    revenue, customers, growth_rate, team_size,
                    mau_bucket, traffic_range, revenue_stage,
                    dau, mau,
                    CASE WHEN mau > 0 THEN dau::float / mau ELSE NULL END as dau_mau_ratio,
                    arpu, arr_growth_rate, grr,
                    active_churn, revenue_churn, nps, quick_ratio
                FROM user_context
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user_result = cur.fetchone()

            user_values = {}
            if user_result:
                user_values = {
                    "revenue": _parse_numeric_value(user_result["revenue"]),
                    "customers": _parse_numeric_value(user_result["customers"]),
                    "growth_rate": _parse_numeric_value(user_result["growth_rate"]),
                    "team_size": _parse_numeric_value(user_result["team_size"]),
                    "mau_bucket": _parse_numeric_value(user_result["mau_bucket"]),
                    "traffic_range": _parse_numeric_value(user_result["traffic_range"]),
                    "revenue_stage": _parse_numeric_value(user_result["revenue_stage"]),
                    "dau_mau_ratio": user_result["dau_mau_ratio"],
                    "arpu": _parse_numeric_value(user_result["arpu"]),
                    "arr_growth_rate": _parse_numeric_value(user_result["arr_growth_rate"]),
                    "grr": _parse_numeric_value(user_result["grr"]),
                    "active_churn": _parse_numeric_value(user_result["active_churn"]),
                    "revenue_churn": _parse_numeric_value(user_result["revenue_churn"]),
                    "nps": _parse_numeric_value(user_result["nps"]),
                    "quick_ratio": _parse_numeric_value(user_result["quick_ratio"]),
                }

    # Get or compute aggregates
    aggregates = get_cached_aggregates(industry)
    if not aggregates:
        aggregates = aggregate_industry_metrics(industry)

    # Add user values and percentile ranks
    metrics: list[PeerPercentile] = []
    for metric, data in aggregates.items():
        user_val = user_values.get(metric)
        user_pct = None

        if user_val is not None and data.sample_count >= K_ANONYMITY_THRESHOLD:
            user_pct = get_user_percentile_rank(user_id, industry, metric, user_val)

        metrics.append(
            PeerPercentile(
                metric=data.metric,
                display_name=data.display_name,
                p10=data.p10,
                p25=data.p25,
                p50=data.p50,
                p75=data.p75,
                p90=data.p90,
                sample_count=data.sample_count,
                user_value=user_val,
                user_percentile=user_pct,
            )
        )

    # Get cache timestamp
    updated_at = None
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT MAX(updated_at)
                FROM peer_benchmark_aggregates
                WHERE industry = %s
                """,
                (industry,),
            )
            result = cur.fetchone()
            if result:
                updated_at = result["max"]

    return PeerBenchmarkResult(
        industry=industry,
        metrics=metrics,
        updated_at=updated_at,
    )
