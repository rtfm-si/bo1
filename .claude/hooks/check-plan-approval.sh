#!/bin/bash
# Hook script to check if plan was approved and should trigger build
# Called by Stop hook after /plan completes

# set -e

# # Read input from stdin
# INPUT=$(cat)

# # Check for _PLAN.md existence and workflow state
# WORKFLOW_STATE=".claude/workflow-state.json"

# # If workflow state indicates approved plan awaiting build
# if [ -f "$WORKFLOW_STATE" ]; then
#     STATE=$(cat "$WORKFLOW_STATE")
#     STATUS=$(echo "$STATE" | jq -r '.status // "none"')

#     if [ "$STATUS" = "plan_approved" ]; then
#         # Clear state and signal to continue with build
#         echo '{"status": "building"}' > "$WORKFLOW_STATE"
#         echo '{"decision": "block", "reason": "Plan approved. Proceeding to execute /build command."}'
#         exit 0
#     fi
# fi

# # No pending approved plan - allow normal stop
# echo '{"continue": true}'
# exit 0
