# Plan: Backlog Triage – Unblock Next Tasks

## Summary

- All implementation tasks in `_TASK.md` are completed or blocked
- Remaining items require user clarification or external action
- This plan identifies what's needed to unblock progress

## Items Requiring User Action

### [LAUNCH][P1] Switch Stripe to Live Mode
**Status:** Ready for manual action
**Action:** User to toggle Stripe keys from test to live per `docs/runbooks/stripe-config.md`

### [EMAIL][P4] Payment Receipt Email Trigger
**Status:** Blocked on Stripe live mode
**Unblocks after:** Stripe live mode switch

### [SOCIAL][P3] Direct Posting to Social Accounts
**Status:** Blocked on user decision
**Action:** User to decide approach (see previous `_PLAN.md` discussion)

## Items Requiring Clarification

### [MONITORING][P1] Kubernetes Deployment Manifest
**Question:** Are we using Kubernetes? Current deployment appears to be direct SSH to DigitalOcean droplet.
**If yes:** Create k8s manifests (deployment, service, ingress, configmap)
**If no:** Mark task as not applicable

### [MONITORING] Grafana Logs "value A"
**Question:** What does "grafana logs: value A" refer to? Need specific requirement.

### [DATA][P2] Data Retention Soft-Delete Behavior
**Question:** What is expected soft-delete behavior?
- Soft-delete keeps row with `deleted_at` timestamp?
- Or hard-delete with audit log?
- Retention period before permanent purge?

## Deferred by Design (No Action Required)

- `[DATA][P2]` DuckDB backend – defer until >100K rows needed
- `[BILLING][P4]` Upgrade prompts near limit – nice-to-have

## User-Owned (Si's Todo)

- `[DOCS][P3]` Help pages content review

---

## Recommended Next Step

**Option A:** Switch Stripe to live mode (unlocks email task, enables production billing)

**Option B:** Clarify Kubernetes question (highest priority monitoring task)

**Option C:** Add new tasks to `_TASK.md` based on priorities

---

_Generated: 2025-12-27_
