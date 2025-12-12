#!/bin/bash
# Autonomous batch: /plan → /build, repeat N times
# Usage: ./batch-run.sh [count] [filter]
# Examples:
#   ./batch-run.sh 5           # Run 5 cycles, any task
#   ./batch-run.sh 10 SEC      # Run 10 cycles, prioritize [SEC] tasks
#   ./batch-run.sh 3 BUG       # Run 3 cycles, prioritize [BUG] tasks
# Output: Full transcript in _BATCH_YYYYMMDD_HHMMSS.log

COUNT=${1:-10}
FILTER=${2:-}
COMPLETED=0
DEFERRED=0
LOGFILE="_BATCH_$(date '+%Y%m%d_%H%M%S').log"

# Use -p (print mode) for non-interactive execution
CLAUDE="claude -p --dangerously-skip-permissions"

if [ -n "$FILTER" ]; then
  echo "=== Starting batch run: $COUNT iterations, filter: [$FILTER] ===" | tee "$LOGFILE" _BATCH_LOG.md
else
  echo "=== Starting batch run: $COUNT iterations ===" | tee "$LOGFILE" _BATCH_LOG.md
fi
echo "Full transcript: $LOGFILE" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

for i in $(seq 1 $COUNT); do
  echo "" | tee -a "$LOGFILE"
  echo "========================================" | tee -a "$LOGFILE"
  echo "=== Cycle $i/$COUNT - $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$LOGFILE"
  echo "========================================" | tee -a "$LOGFILE"
  echo "" | tee -a "$LOGFILE"

  # Plan phase
  echo "--- PLAN PHASE ---" | tee -a "$LOGFILE"
  if [ -n "$FILTER" ]; then
    PLAN_CMD="/plan $FILTER"
  else
    PLAN_CMD="/plan"
  fi
  if $CLAUDE "$PLAN_CMD" 2>&1 | tee -a "$LOGFILE"; then
    TASK=$(grep -m1 "^# Plan:" _PLAN.md 2>/dev/null | sed 's/^# Plan: //' || echo "unknown")
    echo "" | tee -a "$LOGFILE"
    echo "Plan created: $TASK" | tee -a "$LOGFILE"

    # Build phase
    echo "" | tee -a "$LOGFILE"
    echo "--- BUILD PHASE ---" | tee -a "$LOGFILE"
    if $CLAUDE "/build" 2>&1 | tee -a "$LOGFILE"; then
      echo "" | tee -a "$LOGFILE"
      echo "$(date '+%Y-%m-%d %H:%M:%S'): ✓ $TASK" | tee -a _BATCH_LOG.md "$LOGFILE"
      ((COMPLETED++))
    else
      echo "" | tee -a "$LOGFILE"
      echo "$(date '+%Y-%m-%d %H:%M:%S'): DEFERRED (build failed) - $TASK" | tee -a _DEFERRED.md "$LOGFILE"
      ((DEFERRED++))
    fi
  else
    TASK=$(grep -m1 "^# Plan:" _PLAN.md 2>/dev/null | sed 's/^# Plan: //' || echo "unknown")
    echo "" | tee -a "$LOGFILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S'): DEFERRED (plan failed) - $TASK" | tee -a _DEFERRED.md "$LOGFILE"
    ((DEFERRED++))
  fi
done

echo "" | tee -a "$LOGFILE"
echo "========================================" | tee -a "$LOGFILE"
echo "=== Batch complete: $COMPLETED completed, $DEFERRED deferred ===" | tee -a "$LOGFILE" _BATCH_LOG.md
echo "Full transcript: $LOGFILE" | tee -a "$LOGFILE"
