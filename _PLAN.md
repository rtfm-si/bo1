# Plan: No Actionable Tasks

## Summary

- All implementable tasks in `_TASK.md` are complete
- Remaining open tasks are blocked, need clarification, or user-owned
- Ready for new task intake or unblocking decisions

## Current Blockers

### Blocked on User Action
- `[LAUNCH][P1]` Switch Stripe to live mode - see `docs/runbooks/stripe-config.md`
- `[EMAIL][P4]` Payment receipt email trigger - blocked on Stripe live mode
- `[SOCIAL][P3]` Direct posting to social accounts - user to decide approach

### Needs Clarification
- `[MONITORING][P1]` Kubernetes deployment manifest - are we using k8s? (current: SSH to droplet)
- `[MONITORING]` Clarify "grafana logs: value A" requirement
- `[DATA][P2]` Clarify data retention soft-delete behavior

### Deferred by Design
- `[DATA][P2]` DuckDB backend - defer until >100K rows
- `[BILLING][P4]` Upgrade prompts near limit - nice-to-have

### User-Owned
- `[DOCS][P3]` Help pages content review (Si's todo)

## Next Steps

Options to proceed:
1. **Unblock Stripe live mode** - highest impact P1 for launch
2. **Clarify k8s question** - if yes, can plan manifest; if no, remove task
3. **Add new tasks** - from product roadmap or user feedback
4. **Run audits** - `/full_audit` to discover new issues
