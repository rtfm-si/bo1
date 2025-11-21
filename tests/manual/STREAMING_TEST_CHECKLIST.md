# SSE Streaming Manual Test Checklist

This checklist provides manual testing procedures for the real-time SSE streaming implementation.

## Prerequisites

- [ ] Docker services running (`make up`)
- [ ] Redis available and healthy
- [ ] PostgreSQL available and healthy
- [ ] Frontend running on http://localhost:5173
- [ ] Backend API running on http://localhost:8000
- [ ] User authenticated and logged in

---

## Test 1: Basic Session Creation and Stream Connection

**Objective:** Verify that a new session establishes SSE connection and receives initial events.

### Steps:
1. Navigate to dashboard (`/dashboard`)
2. Click "New Meeting" button
3. Enter problem statement: "Should we invest $50K in marketing automation?"
4. Submit the form
5. Observe meeting page loads with session ID in URL
6. Check browser console for SSE connection logs

### Expected Results:
- [ ] Meeting page loads successfully
- [ ] Session ID visible in URL (e.g., `/meeting/bo1_abc123`)
- [ ] Connection status indicator shows "Connected" (green dot)
- [ ] Console logs show: `[SSE] Connection established`
- [ ] No console errors

---

## Test 2: Decomposition Events Display

**Objective:** Verify decomposition events are received and rendered correctly.

### Steps:
1. Start new session with problem: "Should we pivot to B2B SaaS?"
2. Wait for decomposition phase to complete
3. Observe event stream

### Expected Results:
- [ ] "Decomposition Started" event appears (optional, may be too fast)
- [ ] "Problem Decomposition Complete" event appears
- [ ] Sub-problems list is displayed with:
  - [ ] Numbered indicators (1, 2, 3...)
  - [ ] Goal text for each sub-problem
  - [ ] Rationale text for each sub-problem
  - [ ] Complexity score badges
  - [ ] Dependencies shown (if any)
- [ ] Badge shows correct count (e.g., "3 sub-problems")

---

## Test 3: Persona Selection Events Display

**Objective:** Verify persona selection events show expert details.

### Steps:
1. Continue from Test 2 (or start new session)
2. Wait for persona selection phase
3. Observe expert selection events

### Expected Results:
- [ ] Multiple "Persona Selected" events appear (3-5 experts)
- [ ] Each persona card shows:
  - [ ] Order number (1, 2, 3...)
  - [ ] Display name (e.g., "Zara Kim (CFO)")
  - [ ] Code badge (e.g., "CFO")
  - [ ] Selection rationale
  - [ ] Domain expertise tags
- [ ] "Persona Selection Complete" event appears
- [ ] Final count badge matches number of selected personas

---

## Test 4: Expert Contributions Display in Real-Time

**Objective:** Verify expert contributions stream in real-time during deliberation.

### Steps:
1. Continue observing the active session
2. Watch initial round and subsequent rounds
3. Enable auto-scroll if needed

### Expected Results:
- [ ] "Initial Round Started" event appears
- [ ] Contribution events stream in real-time (within 1-2 seconds of generation)
- [ ] Each contribution shows:
  - [ ] Expert avatar/initials
  - [ ] Expert name
  - [ ] Round number badge
  - [ ] "Initial" or "Follow-up" badge
  - [ ] Full contribution text (readable, formatted)
- [ ] Auto-scroll moves to newest contribution
- [ ] Contributions appear in chronological order

---

## Test 5: Facilitator Decisions Display

**Objective:** Verify facilitator decisions are shown with action and reasoning.

### Steps:
1. Continue observing active session
2. Look for facilitator decision events between rounds

### Expected Results:
- [ ] Facilitator decision events appear between rounds
- [ ] Each decision shows:
  - [ ] Action badge (Continue, Proceed to Voting, etc.)
  - [ ] Reasoning text
  - [ ] Next speaker (if action is "continue")
  - [ ] Round number
- [ ] Badge color matches action type:
  - [ ] Blue/Info for "Continue"
  - [ ] Green/Success for "Proceed to Voting"
  - [ ] Yellow/Warning for "Research" or "Clarification"

---

## Test 6: Convergence Progress Display

**Objective:** Verify convergence checks show progress towards consensus.

### Steps:
1. Continue observing active session
2. Watch for convergence check events (after each round)

### Expected Results:
- [ ] Convergence event appears after each round
- [ ] Progress bar shows:
  - [ ] Current score vs threshold
  - [ ] Percentage of threshold
  - [ ] Visual progress (bar fills as score increases)
  - [ ] Color changes based on progress:
    - [ ] Gray/Neutral < 50%
    - [ ] Yellow/Warning 50-70%
    - [ ] Blue/Info 70-85%
    - [ ] Green/Success >= 85%
- [ ] Badge shows "Converged" or "In Progress"
- [ ] Round counter shows "Round X / Y"

---

## Test 7: Voting Phase Display

**Objective:** Verify voting phase shows all expert recommendations.

### Steps:
1. Wait for session to reach voting phase
2. Observe voting events

### Expected Results:
- [ ] "Voting Phase Started" event appears with gradient background
- [ ] Expert list shows all participating experts
- [ ] Individual vote/recommendation events display:
  - [ ] Expert name and code
  - [ ] Recommendation text
  - [ ] Confidence percentage badge (color-coded):
    - [ ] Green >= 80%
    - [ ] Blue 60-80%
    - [ ] Yellow < 60%
  - [ ] Reasoning section
  - [ ] Conditions list (if provided)
- [ ] "Voting Complete" event shows consensus level

---

## Test 8: Synthesis Display with Markdown

**Objective:** Verify synthesis report is displayed with proper formatting.

### Steps:
1. Wait for synthesis phase (near end of deliberation)
2. Observe synthesis complete event

### Expected Results:
- [ ] "Synthesis Complete" event appears
- [ ] Green success indicator and checkmark
- [ ] Word count badge displayed
- [ ] Synthesis text shows:
  - [ ] Markdown headings (if present)
  - [ ] Bullet points (if present)
  - [ ] Proper line breaks
  - [ ] Readable formatting in white/dark background box
- [ ] Text is scrollable if long

---

## Test 9: Sub-Problem Progress Display

**Objective:** Verify sub-problem completion shows metrics.

### Steps:
1. If multiple sub-problems, wait for first to complete
2. Observe sub-problem complete event

### Expected Results:
- [ ] "Sub-Problem Complete" event appears
- [ ] Green gradient background
- [ ] Checkmark icon
- [ ] Badge shows sub-problem number
- [ ] Goal text displayed
- [ ] Metrics grid shows:
  - [ ] Duration (formatted as "Xm Ys")
  - [ ] Cost (formatted as "$0.XXXX")
  - [ ] Contribution count
  - [ ] Expert count
- [ ] Expert panel badges listed

---

## Test 10: Phase Cost Breakdown Table

**Objective:** Verify cost breakdown displays in table format.

### Steps:
1. Wait for deliberation to complete
2. Observe phase cost breakdown event

### Expected Results:
- [ ] "Phase Cost Breakdown" event appears
- [ ] Total cost badge at top
- [ ] Table displays:
  - [ ] Phase names (formatted, e.g., "Round 1 Deliberation")
  - [ ] Cost per phase (formatted as "$0.XXXX")
  - [ ] Percentage of total
  - [ ] Visual progress bar for each phase
- [ ] Phases sorted by cost (highest first)
- [ ] Table is scrollable if many phases

---

## Test 11: Deliberation Complete Summary

**Objective:** Verify completion event shows full summary.

### Steps:
1. Wait for deliberation to complete
2. Observe "Deliberation Complete" event

### Expected Results:
- [ ] Large gradient card with success styling
- [ ] Large checkmark icon
- [ ] "Deliberation Complete" heading
- [ ] Stop reason displayed (e.g., "Consensus Reached")
- [ ] Metrics grid shows:
  - [ ] Total cost (green, prominent)
  - [ ] Duration (formatted)
  - [ ] Total rounds
  - [ ] Total contributions
- [ ] Token count badge
- [ ] Session ID displayed
- [ ] "View Results" button appears in sidebar

---

## Test 12: Error Event Display

**Objective:** Verify errors are displayed with appropriate styling.

### Steps:
1. Manually trigger an error (if possible, e.g., kill Redis)
2. OR observe if any errors occur naturally

### Expected Results:
- [ ] Error event appears with:
  - [ ] Red left border
  - [ ] Red/orange background
  - [ ] Error icon
  - [ ] Error heading
  - [ ] Error message text
  - [ ] Error type badge
  - [ ] "Recoverable" or "Fatal" badge
  - [ ] Node name (if available)
  - [ ] Help text about recovery

---

## Test 13: Pause and Resume Maintains Stream

**Objective:** Verify pause/resume works correctly with event streaming.

### Steps:
1. Start new session
2. Wait for 1-2 rounds to complete
3. Click "Pause" button
4. Wait 10 seconds
5. Click "Resume" button
6. Observe stream

### Expected Results:
- [ ] Pause button changes to "Resume"
- [ ] Events stop streaming during pause
- [ ] Connection status may show "Retrying" then "Connected" on resume
- [ ] After resume, events continue from where they left off
- [ ] No duplicate events
- [ ] No missing events (verify by round numbers)

---

## Test 14: Reconnection After Network Drop

**Objective:** Verify automatic reconnection after brief network disruption.

### Steps:
1. Start new session
2. Open browser DevTools > Network tab
3. Throttle to "Offline" for 5 seconds
4. Restore to "Online"
5. Observe stream

### Expected Results:
- [ ] Connection status changes to "Retrying"
- [ ] Retry count increments (1/3, 2/3)
- [ ] Connection automatically re-establishes
- [ ] Status changes back to "Connected"
- [ ] Events resume streaming
- [ ] Console shows retry logs: `[SSE] Retrying in Xms...`

---

## Test 15: Multiple Sessions Isolation

**Objective:** Verify events from different sessions don't mix.

### Steps:
1. Open two browser tabs
2. Start session A in tab 1 with problem: "Problem A"
3. Start session B in tab 2 with problem: "Problem B"
4. Observe both streams simultaneously

### Expected Results:
- [ ] Tab 1 shows only events for Session A
- [ ] Tab 2 shows only events for Session B
- [ ] No event mixing between sessions
- [ ] Each session has unique session ID in URL
- [ ] Each session progresses independently

---

## Test 16: Dark Mode Compatibility

**Objective:** Verify all event components work in dark mode.

### Steps:
1. Toggle system dark mode (or use browser DevTools)
2. Observe event stream in dark mode

### Expected Results:
- [ ] All event cards have proper dark mode colors
- [ ] Text is readable (sufficient contrast)
- [ ] Badges have appropriate dark mode colors
- [ ] Background colors are dark but distinguishable
- [ ] Border colors are visible
- [ ] No pure white or pure black (except intentional)

---

## Test 17: Long Content Handling

**Objective:** Verify long contributions and synthesis are handled properly.

### Steps:
1. Start session with complex problem requiring detailed analysis
2. Observe contributions with 500+ words
3. Observe synthesis with 1000+ words

### Expected Results:
- [ ] Long text doesn't break layout
- [ ] Text wraps properly
- [ ] Scrollable within event card (if needed)
- [ ] No horizontal overflow
- [ ] Line breaks preserved
- [ ] "View more" or expansion UI (if implemented)

---

## Test 18: Auto-Scroll Toggle

**Objective:** Verify auto-scroll can be enabled/disabled.

### Steps:
1. Start new session
2. Disable auto-scroll checkbox
3. Let several events stream in
4. Manually scroll up to older events
5. Enable auto-scroll checkbox

### Expected Results:
- [ ] With auto-scroll ON: New events automatically scroll into view
- [ ] With auto-scroll OFF: View stays at current scroll position
- [ ] Manual scroll overrides auto-scroll temporarily
- [ ] Toggle works immediately without page refresh

---

## Test 19: Generic Event Fallback

**Objective:** Verify unknown event types display gracefully.

### Steps:
1. (Developer test) Manually publish unknown event type via Redis CLI
2. OR wait for any unexpected event types

### Expected Results:
- [ ] Generic event component displays
- [ ] Event type shown (formatted)
- [ ] "View event data" expandable section
- [ ] Raw JSON data shown in `<pre>` tag
- [ ] No console errors or crashes

---

## Test 20: Performance with Many Events

**Objective:** Verify UI remains responsive with 50+ events.

### Steps:
1. Start complex problem requiring many rounds
2. Let deliberation run for 10+ rounds
3. Observe frontend performance

### Expected Results:
- [ ] UI remains responsive (no lag)
- [ ] Scrolling is smooth
- [ ] New events render quickly
- [ ] No memory leaks (check browser Task Manager)
- [ ] Page doesn't crash
- [ ] Event count: 50+ events displayed

---

## Browser Compatibility Checklist

Test the above scenarios in multiple browsers:

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

---

## Post-Testing Checklist

After completing all tests:

- [ ] No console errors in any test
- [ ] All event types render correctly
- [ ] Real-time streaming works reliably
- [ ] Dark mode works for all components
- [ ] Auto-scroll functions as expected
- [ ] Pause/resume maintains state
- [ ] Error handling works gracefully
- [ ] Performance is acceptable (no lag)

---

## Known Issues / Notes

Document any issues found during testing:

1.
2.
3.

---

## Sign-off

**Tester Name:** ________________________

**Date:** ________________________

**Build/Commit:** ________________________

**Pass/Fail:** ________________________

**Notes:**
