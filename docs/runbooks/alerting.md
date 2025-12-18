# Alerting Runbook

## Overview

Bo1 uses Prometheus + Alertmanager + ntfy for the alerting pipeline:
- **Prometheus**: Evaluates alert rules, sends firing alerts to Alertmanager
- **Alertmanager**: Groups, deduplicates, routes alerts to receivers
- **ntfy**: Delivers push notifications (self-hosted at ntfy.boardof.one)

## Verifying Alertmanager is Running

```bash
# Check service status
docker compose -f docker-compose.infrastructure.yml ps alertmanager

# Check health
curl -s http://localhost:9093/-/healthy
# Expected: OK

# View Alertmanager UI
open http://localhost:9093
```

## Verifying Prometheus→Alertmanager Connection

1. Open Prometheus UI: http://localhost:9090
2. Navigate to Status → Targets
3. Confirm `alertmanager:9093` appears as a target (may be under "Alertmanagers" section)
4. Or check Status → Runtime & Build Information for alertmanager discovery

## Subscribe to Alerts

### Option 1: ntfy Web UI
1. Go to https://ntfy.boardof.one/bo1-prod-alerts
2. Click "Subscribe" in browser

### Option 2: ntfy Mobile App
1. Install ntfy app (iOS/Android)
2. Add server: `https://ntfy.boardof.one`
3. Subscribe to topic: `bo1-prod-alerts`

### Option 3: CLI
```bash
# Stream alerts to terminal
curl -s https://ntfy.boardof.one/bo1-prod-alerts/raw
```

## Testing the Alert Pipeline

### 1. Send Test Alert to Alertmanager
```bash
curl -XPOST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning"
    },
    "annotations": {
      "summary": "Test alert from runbook"
    }
  }]'
```

### 2. Send Test Alert Directly to ntfy
```bash
curl -d "Test notification from bo1" \
  https://ntfy.boardof.one/bo1-prod-alerts
```

### 3. Trigger Real Alert (Development Only)
Stop a monitored service briefly to trigger an alert rule.

## Alert Routing

| Severity | Receiver | ntfy Priority | Repeat Interval |
|----------|----------|---------------|-----------------|
| critical | critical | urgent | 1h |
| warning | warning | default | 4h |
| other | default | - (webhook only) | 4h |

## Troubleshooting

### Alerts Not Firing
1. Check Prometheus alert rules: http://localhost:9090/alerts
2. Verify rule syntax: `promtool check rules /path/to/alert_rules.yml`
3. Check Prometheus logs: `docker compose logs prometheus`

### Alerts Not Reaching ntfy
1. Check Alertmanager logs: `docker compose -f docker-compose.infrastructure.yml logs alertmanager`
2. Verify ntfy is reachable: `curl https://ntfy.boardof.one/v1/health`
3. Check Alertmanager config: http://localhost:9093/#/status

### Silencing Alerts
1. Open Alertmanager UI: http://localhost:9093
2. Click "Silences" → "New Silence"
3. Set matchers (e.g., `alertname="NoisyAlert"`)
4. Set duration and save

## Files

- Alert rules: `monitoring/prometheus/alert_rules.yml`
- Alertmanager config: `infra/alertmanager/config.yml`
- Prometheus config: `monitoring/prometheus.yml`
