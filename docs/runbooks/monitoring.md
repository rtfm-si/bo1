# Uptime Monitoring Runbook

## Overview

Board of One uses UptimeRobot for external uptime monitoring. This provides independent verification that the service is accessible from the public internet.

## Monitor Configuration

### Primary Monitors

| Monitor | URL | Type | Interval | Keyword |
|---------|-----|------|----------|---------|
| Homepage | `https://boardof.one` | HTTPS | 5 min | N/A |
| Health API | `https://boardof.one/api/v1/health` | HTTPS | 5 min | `"status":"healthy"` |

### Health Endpoint Response

The `/api/v1/health` endpoint returns:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:00:00.000000",
  "details": {
    "version": "1.0.0",
    "api": "Board of One",
    "build_timestamp": "...",
    "git_commit": "..."
  }
}
```

UptimeRobot keyword monitor checks for `"status":"healthy"` to verify the API is functioning correctly.

## Alert Configuration

### Alert Contacts

- **Primary**: Admin email (configured in UptimeRobot dashboard)
- **Secondary**: NTFY webhook (optional, see below)

### NTFY Integration (Optional)

To receive push notifications via NTFY:

1. Set `NTFY_TOPIC` environment variable in production
2. Configure UptimeRobot webhook alert contact:
   - URL: `https://ntfy.sh/{NTFY_TOPIC}`
   - POST method
   - Body: `{"topic": "{NTFY_TOPIC}", "message": "*monitorFriendlyName* is *alertTypeFriendlyName*"}`

## Status Page

Public status page: https://stats.uptimerobot.com/boardofone

The admin dashboard displays a status badge linking to this page.

## Incident Response

When UptimeRobot alerts:

1. Check the admin dashboard for internal health status
2. Review `/api/v1/ready` for component-level health
3. Check Grafana dashboards for metrics anomalies
4. Review Loki logs for errors
5. Follow [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md) for escalation procedures

## Related Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/api/v1/health` | Liveness probe | Public |
| `/api/v1/ready` | Readiness probe (Postgres, Redis) | Public |
| `/api/v1/health/db` | PostgreSQL health | Public |
| `/api/v1/health/redis` | Redis health | Public |
| `/api/v1/health/detailed` | Event queue + circuit breakers | Public |
