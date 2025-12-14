# Plan: Backlog Complete - No Implementable Tasks

## Summary

- All implementable code tasks in `_TASK.md` are complete (`[x]`)
- Remaining items are blocked, deferred, or require manual external action
- No code implementation plan needed at this time

## Remaining Items (Not Implementable)

### External/Manual Setup (User action required)
- Stripe account setup + products/prices (manual)
- DPA signing with vendors (legal)
- GitHub secrets configuration (DevOps)
- Domain purchase + DNS (infrastructure)
- SSL/TLS + Let's Encrypt (infrastructure)
- Uptime monitoring (UptimeRobot) (infrastructure)
- Blue-green deployment setup (DevOps)
- Deploy Prometheus/Grafana to prod (DevOps)
- Configure production Alertmanager (DevOps)
- Switch Stripe to live mode (business decision)
- Test emergency access procedures (manual)

### Blocked on Dependencies
- Payment receipt email - blocked on Stripe live mode
- Direct social posting - blocked on user decision (Option A vs B)

### Deferred by Design
- DuckDB backend - defer until >100K row datasets needed
- Upgrade prompts near limit - nice-to-have

### Needs Clarification
- Kubernetes manifest - awaiting decision on K8s usage
- MCP prompt scope - unclear requirement

## Status

**Backlog clear** - no implementable code tasks remain.

User input needed to:
1. Unblock Stripe-dependent features (live mode switch)
2. Decide on direct social posting (Option A vs B)
3. Clarify Kubernetes usage
4. Prioritize any manual setup tasks
