# Service Level Indicators (SLIs) and Objectives (SLOs)

## Overview

This document defines the SLIs and SLOs for Board of One (bo1). These metrics guide alerting, incident response, and capacity planning.

## SLIs and SLOs

### 1. Availability

- **SLI**: Proportion of successful HTTP requests (non-5xx) to total requests
- **Formula**: `sum(rate(http_requests_total{status!~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- **SLO Target**: 99.5% over 30-day window
- **Error Budget**: 0.5% (3.6 hours/month)

### 2. Latency

- **SLI**: 95th percentile response time for API requests
- **Formula**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- **SLO Target**: p95 < 500ms for 95% of 5-minute windows
- **Exclusions**: SSE streaming endpoints, file uploads

### 3. Error Rate

- **SLI**: Rate of 5xx errors relative to total requests
- **Formula**: `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- **SLO Target**: < 0.5% over 5-minute windows
- **Alert Threshold**: > 1% for 5 minutes

### 4. Session Completion

- **SLI**: Proportion of started sessions that complete successfully
- **Formula**: `sum(bo1_sessions_total{status="completed"}) / sum(bo1_sessions_total{status="started"})`
- **SLO Target**: 95% completion rate
- **Note**: Excludes user-cancelled sessions

## Alerting Thresholds

| Alert | Condition | Duration | Severity |
|-------|-----------|----------|----------|
| HighErrorRate | error_rate > 1% | 5m | warning |
| HighErrorRateCritical | error_rate > 5% | 2m | critical |
| HighLatencyP95 | p95 > 1s | 5m | warning |
| HighLatencyP95Critical | p95 > 2s | 2m | critical |
| LowAvailability | availability < 99% | 10m | critical |
| SessionCompletionLow | completion < 90% | 15m | warning |
| BurnRateHigh | 1h burn > 10% budget | 1h | warning |

## Error Budget Policy

1. **Budget Remaining > 50%**: Normal operations, deploy freely
2. **Budget Remaining 25-50%**: Increased review for risky changes
3. **Budget Remaining < 25%**: Freeze non-critical deploys, focus on reliability
4. **Budget Exhausted**: Halt all changes except reliability fixes

## Measurement Windows

- **Short window**: 5 minutes (alerting)
- **Medium window**: 1 hour (burn rate)
- **Long window**: 30 days (SLO compliance)

## Review Cadence

- Weekly: Review burn rate and incidents
- Monthly: Review SLO compliance, adjust targets if needed
- Quarterly: Full SLI/SLO review with stakeholders
