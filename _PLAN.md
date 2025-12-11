# Plan: Create Grafana Operational Dashboards [MONITORING-DASHBOARDS]

## Summary

- Create API dashboard (request rate, latency, errors by endpoint)
- Create Deliberation dashboard (session metrics, LLM costs, round times)
- Create Cost dashboard (daily spend, per-user breakdown, model costs)
- Create Infrastructure dashboard (Redis, Postgres, container metrics)

## Implementation Steps

1. **Create API Dashboard**
   - `infra/grafana/dashboards/api.json`
   - Panels: request rate, latency histogram, error rate by endpoint, status code breakdown, top 10 slowest endpoints

2. **Create Deliberation Dashboard**
   - `infra/grafana/dashboards/deliberation.json`
   - Panels: sessions started/completed, rounds per session, avg session duration, completion rate, active sessions gauge

3. **Create Cost Dashboard**
   - `infra/grafana/dashboards/cost.json`
   - Panels: daily LLM spend, cost by model, cost by user (top 10), cumulative monthly spend, cost per session avg

4. **Create Infrastructure Dashboard**
   - `infra/grafana/dashboards/infrastructure.json`
   - Panels: container CPU/memory, Redis memory/connections, Postgres connections/query time, disk usage

5. **Update Grafana provisioning**
   - Ensure all dashboards auto-load from dashboards directory
   - Verify datasource UID matches across all dashboards

## Tests

- **Unit tests:**
  - Validate JSON syntax: `python -c "import json; json.load(open('...'))" for each dashboard

- **Integration tests:**
  - Start monitoring profile: `docker-compose --profile monitoring up`
  - Access Grafana at localhost:3001
  - Verify all 4 dashboards appear and panels render

- **Manual validation:**
  - Generate some API traffic, verify request metrics populate
  - Run a test session, verify deliberation metrics populate
  - Check infrastructure panels show container metrics

## Dependencies & Risks

- **Dependencies:**
  - Prometheus metrics already instrumented (✅ complete)
  - Grafana + Prometheus in docker-compose (✅ complete)
  - Custom bo1_* metrics exposed from middleware/metrics.py

- **Risks:**
  - Some metrics may not exist yet → use `rate(http_requests_total[5m])` as fallback
  - Container metrics require cAdvisor or similar → may show empty initially
