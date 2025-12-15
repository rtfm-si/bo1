# API Coverage Runner Prompt

Execute comprehensive API coverage testing by exercising all endpoints through their real UI callers using Playwright MCP.

---

## A) Setup

### 1. Environment Configuration
```
BASE_URL: http://localhost:5173 (frontend)
API_URL: http://localhost:8000 (backend)
```

### 2. Prerequisites Check
- Verify app is running: `curl http://localhost:5173` and `curl http://localhost:8000/api/health`
- If not running: `make up` or start dev servers

### 3. Playwright MCP Initialization
Use `mcp__playwright__browser_navigate` to open BASE_URL. Configure:
- Console capture: Use `mcp__playwright__browser_console_messages` after each navigation
- Network capture: Use `mcp__playwright__browser_network_requests` after each action

### 4. API Call Recording
For each UI interaction, capture via `browser_network_requests`:
- Method, URL, status code, duration
- Response shape (JSON keys only, no sensitive data)
- Tag with triggering UI step

### 5. Test Credentials
Use test account if available, otherwise create via UI signup flow:
- Email: `test-coverage@example.com`
- If auth required and no credentials, flag endpoint and continue

---

## B) Coverage Strategy

### Endpoint Categories & Trigger Methods

#### Category 1: Health & Status (NO UI CALLER)
| Endpoint | Method | UI Caller |
|----------|--------|-----------|
| `/api/health` | GET | None (k8s probe) |
| `/api/health/db` | GET | None (k8s probe) |
| `/api/health/redis` | GET | None (k8s probe) |
| `/api/health/anthropic` | GET | None (k8s probe) |
| `/api/ready` | GET | None (k8s probe) |

**Action**: Skip - no UI trigger, mark as "server-only"

#### Category 2: Authentication
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `/api/v1/auth/me` | GET | Header component | Page load after login |
| `/api/v1/auth/google/sheets/status` | GET | Settings/Integrations | Navigate to integrations |
| `/api/v1/auth/google/sheets/connect` | GET | Connect button | Click Google Sheets connect |
| `/api/v1/auth/google/sheets/disconnect` | DELETE | Disconnect button | Click disconnect |

#### Category 3: Sessions (Meetings)
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `POST /api/v1/sessions` | POST | New Meeting page | Fill form, submit |
| `GET /api/v1/sessions` | GET | Dashboard | Navigate to dashboard |
| `GET /api/v1/sessions/{id}` | GET | Meeting detail | Navigate to /meeting/{id} |
| `DELETE /api/v1/sessions/{id}` | DELETE | Delete button | Click delete on meeting |
| `POST /api/v1/sessions/{id}/start` | POST | Start button | Click start deliberation |
| `POST /api/v1/sessions/{id}/pause` | POST | Pause button | Click pause |
| `POST /api/v1/sessions/{id}/resume` | POST | Resume button | Click resume |
| `POST /api/v1/sessions/{id}/kill` | POST | Kill button | Click stop |
| `POST /api/v1/sessions/{id}/terminate` | POST | Terminate button | Click terminate |
| `GET /api/v1/sessions/{id}/events` | GET | Meeting page | Page load |
| `GET /api/v1/sessions/{id}/stream` | GET (SSE) | Meeting page | SSE subscription |
| `POST /api/v1/sessions/{id}/clarify` | POST | Clarification form | Submit clarification |
| `POST /api/v1/sessions/{id}/extract-tasks` | POST | Extract tasks button | Click extract |
| `GET /api/v1/sessions/{id}/actions` | GET | Actions panel | Meeting page load |
| `PATCH /api/v1/sessions/{id}/actions/{taskId}` | PATCH | Kanban drag | Drag action card |
| `GET /api/v1/sessions/{id}/costs` | GET | Cost breakdown | Meeting page |
| `GET /api/v1/sessions/{id}/export` | GET | Export button | Click export |
| `POST /api/v1/sessions/{id}/share` | POST | Share button | Create share link |
| `GET /api/v1/sessions/{id}/share` | GET | Share modal | Open share modal |
| `DELETE /api/v1/sessions/{id}/share/{token}` | DELETE | Revoke button | Revoke share |
| `GET /api/v1/sessions/{id}/projects` | GET | Project selector | Meeting page |
| `POST /api/v1/sessions/{id}/projects` | POST | Link project | Select project to link |
| `DELETE /api/v1/sessions/{id}/projects/{projectId}` | DELETE | Unlink button | Unlink project |
| `GET /api/v1/sessions/{id}/suggest-projects` | GET | Suggestions | Open project suggestions |
| `POST /api/v1/sessions/{id}/create-suggested-project` | POST | Create suggestion | Accept suggestion |

#### Category 4: Actions
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/actions` | GET | Actions page | Navigate to /actions |
| `GET /api/v1/actions/{id}` | GET | Action detail | Navigate to /actions/{id} |
| `DELETE /api/v1/actions/{id}` | DELETE | Delete button | Click delete action |
| `POST /api/v1/actions/{id}/start` | POST | Start button | Click start |
| `POST /api/v1/actions/{id}/complete` | POST | Complete button | Click complete |
| `PATCH /api/v1/actions/{id}/status` | PATCH | Status dropdown | Change status |
| `GET /api/v1/actions/gantt` | GET | Gantt view | Navigate to gantt |
| `GET /api/v1/actions/stats` | GET | Dashboard | Dashboard load (heatmap) |
| `GET /api/v1/actions/reminders` | GET | Header | Page load (notifications) |
| `GET /api/v1/actions/{id}/reminder-settings` | GET | Reminder modal | Open reminder settings |
| `PATCH /api/v1/actions/{id}/reminder-settings` | PATCH | Save button | Save reminders |
| `POST /api/v1/actions/{id}/snooze-reminder` | POST | Snooze button | Snooze reminder |
| `GET /api/v1/actions/{id}/updates` | GET | Activity tab | Open activity |
| `POST /api/v1/actions/{id}/updates` | POST | Add update | Add progress note |
| `POST /api/v1/actions/{id}/replan` | POST | Replan button | Request replan |
| `PATCH /api/v1/actions/{id}/dates` | PATCH | Gantt drag | Drag to reschedule |
| `GET /api/v1/actions/{id}/dependencies` | GET | Dependencies tab | View dependencies |
| `POST /api/v1/actions/{id}/dependencies` | POST | Add dependency | Add dependency |
| `DELETE /api/v1/actions/{id}/dependencies/{depId}` | DELETE | Remove button | Remove dependency |
| `GET /api/v1/actions/{id}/tags` | GET | Tags panel | View tags |
| `PUT /api/v1/actions/{id}/tags` | PUT | Save tags | Update tags |
| `PATCH /api/v1/actions/{id}/progress` | PATCH | Progress slider | Update progress |
| `GET /api/v1/actions/{id}/variance` | GET | Variance panel | View variance |

#### Category 5: Projects
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/projects` | GET | Projects page | Navigate to /projects |
| `POST /api/v1/projects` | POST | Create button | Create project modal |
| `GET /api/v1/projects/{id}` | GET | Project detail | Navigate to /projects/{id} |
| `PATCH /api/v1/projects/{id}` | PATCH | Edit form | Update project |
| `DELETE /api/v1/projects/{id}` | DELETE | Delete button | Delete project |
| `PATCH /api/v1/projects/{id}/status` | PATCH | Status dropdown | Change status |
| `GET /api/v1/projects/{id}/actions` | GET | Project page | Project detail load |
| `POST /api/v1/projects/{id}/actions/{actionId}` | POST | Assign button | Assign action |
| `DELETE /api/v1/projects/{id}/actions/{actionId}` | DELETE | Unassign | Remove action |
| `GET /api/v1/projects/{id}/gantt` | GET | Gantt tab | View project gantt |
| `GET /api/v1/projects/{id}/sessions` | GET | Sessions tab | View linked sessions |
| `POST /api/v1/projects/{id}/sessions` | POST | Link button | Link session |
| `DELETE /api/v1/projects/{id}/sessions/{sessionId}` | DELETE | Unlink | Unlink session |
| `POST /api/v1/projects/{id}/meetings` | POST | New meeting | Create meeting for project |
| `GET /api/v1/projects/autogenerate-suggestions` | GET | Autogen modal | Open autogen |
| `POST /api/v1/projects/autogenerate` | POST | Generate button | Create autogen projects |
| `GET /api/v1/projects/unassigned-count` | GET | Dashboard | Dashboard load |

#### Category 6: Context
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/context` | GET | Context page | Navigate to /context |
| `PUT /api/v1/context` | PUT | Save button | Save context |
| `DELETE /api/v1/context` | DELETE | Reset button | Reset context |
| `GET /api/v1/context/refresh-check` | GET | Banner | Page load |
| `POST /api/v1/context/dismiss-refresh` | POST | Dismiss button | Dismiss banner |
| `POST /api/v1/context/enrich` | POST | Enrich button | Enrich from URL |
| `GET /api/v1/context/insights` | GET | Insights tab | View insights |
| `PATCH /api/v1/context/insights/{hash}` | PATCH | Rate button | Rate insight |
| `DELETE /api/v1/context/insights/{hash}` | DELETE | Delete button | Delete insight |
| `GET /api/v1/context/pending-updates` | GET | Updates panel | View pending |
| `POST /api/v1/context/pending-updates/{id}/approve` | POST | Approve | Approve update |
| `DELETE /api/v1/context/pending-updates/{id}` | DELETE | Dismiss | Dismiss update |

#### Category 7: Tags
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/tags` | GET | Tag manager | Open tag management |
| `POST /api/v1/tags` | POST | Create button | Create tag |
| `PATCH /api/v1/tags/{id}` | PATCH | Edit button | Edit tag |
| `DELETE /api/v1/tags/{id}` | DELETE | Delete button | Delete tag |

#### Category 8: User & Billing
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/user/preferences` | GET | Settings | Navigate to /settings |
| `PATCH /api/v1/user/preferences` | PATCH | Save button | Save preferences |
| `GET /api/v1/user/usage` | GET | Usage panel | Settings/billing load |
| `GET /api/v1/user/tier-info` | GET | Tier badge | Header/settings load |
| `GET /api/v1/billing/plan` | GET | Billing page | Navigate to /settings/billing |
| `GET /api/v1/billing/usage` | GET | Usage section | Billing page load |
| `POST /api/v1/billing/checkout` | POST | Upgrade button | Click upgrade |
| `POST /api/v1/billing/portal` | POST | Manage button | Open billing portal |
| `GET /api/v1/user/export` | GET | Export button | GDPR export |
| `DELETE /api/v1/user/delete` | DELETE | Delete account | Delete account flow |
| `GET /api/v1/user/retention` | GET | Retention settings | Privacy settings |
| `PATCH /api/v1/user/retention` | PATCH | Save button | Update retention |
| `GET /api/v1/user/email-preferences` | GET | Email settings | Email prefs page |
| `PATCH /api/v1/user/email-preferences` | PATCH | Save button | Update email prefs |
| `GET /api/v1/user/value-metrics` | GET | Dashboard | Dashboard load |

#### Category 9: Workspaces
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/workspaces` | GET | Workspace selector | Header dropdown |
| `POST /api/v1/workspaces` | POST | Create button | Create workspace |
| `GET /api/v1/workspaces/{id}` | GET | Workspace page | Navigate to workspace |
| `PATCH /api/v1/workspaces/{id}` | PATCH | Settings form | Update workspace |
| `DELETE /api/v1/workspaces/{id}` | DELETE | Delete button | Delete workspace |
| `GET /api/v1/workspaces/{id}/members` | GET | Members tab | View members |
| `POST /api/v1/workspaces/{id}/members` | POST | Add member | Add member |
| `DELETE /api/v1/workspaces/{id}/members/{userId}` | DELETE | Remove button | Remove member |
| `POST /api/v1/workspaces/{id}/join-request` | POST | Join button | Request to join |
| `GET /api/v1/workspaces/{id}/join-requests` | GET | Requests panel | View requests |
| `POST /api/v1/workspaces/{id}/join-requests/{id}/approve` | POST | Approve button | Approve request |
| `POST /api/v1/workspaces/{id}/join-requests/{id}/reject` | POST | Reject button | Reject request |

#### Category 10: Onboarding
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/onboarding/status` | GET | Checklist | Dashboard load |
| `POST /api/v1/onboarding/step` | POST | Complete step | Mark step done |
| `POST /api/v1/onboarding/tour/complete` | POST | Tour end | Complete tour |
| `POST /api/v1/onboarding/skip` | POST | Skip button | Skip onboarding |

#### Category 11: Datasets (Data Analysis)
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/datasets` | GET | Datasets page | Navigate to /data |
| `GET /api/v1/datasets/{id}` | GET | Dataset detail | Open dataset |
| `POST /api/v1/datasets/upload` | POST | Upload form | Upload CSV |
| `DELETE /api/v1/datasets/{id}` | DELETE | Delete button | Delete dataset |
| `POST /api/v1/datasets/{id}/profile` | POST | Profile button | Generate profile |
| `POST /api/v1/datasets/{id}/query` | POST | Query input | Run query |
| `POST /api/v1/datasets/{id}/chart` | POST | Chart button | Generate chart |
| `POST /api/v1/datasets/{id}/ask` | POST (SSE) | Chat input | Ask question |
| `GET /api/v1/datasets/{id}/conversations` | GET | Conversations | View history |

#### Category 12: Mentor Chat
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `POST /api/v1/mentor/chat` | POST (SSE) | Chat input | Send message |
| `GET /api/v1/mentor/personas` | GET | Persona picker | Open chat |
| `GET /api/v1/mentor/conversations` | GET | History | View history |
| `DELETE /api/v1/mentor/conversations/{id}` | DELETE | Delete button | Delete conversation |

#### Category 13: Feedback
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `POST /api/v1/feedback` | POST | Feedback modal | Submit feedback |

#### Category 14: Share (Public)
| Endpoint | Method | UI Caller | Trigger |
|----------|--------|-----------|---------|
| `GET /api/v1/share/{token}` | GET | Share page | Navigate to /share/{token} |

#### Category 15: Admin (Server-Only SSR)
All `/api/admin/*` endpoints are called via SSR (+page.server.ts), not directly from browser.
**Action**: Test via admin page navigation, verify network calls happen server-side.

#### Category 16: Webhooks & Internal (NO UI CALLER)
| Endpoint | Method | Reason |
|----------|--------|--------|
| `POST /api/v1/billing/webhook` | POST | Stripe calls directly |
| `POST /api/v1/csp-report` | POST | Browser sends automatically |
| `POST /api/v1/analytics/page-view` | POST | JS tracker sends |
| `POST /api/v1/metrics/client` | POST | Error tracker sends |
| `GET /api/v1/email/unsubscribe` | GET | Email link |

**Action**: Skip - mark as "no UI caller"

---

### Journey Plan

Execute these journeys in order to maximize coverage:

#### Journey 1: Authentication & Onboarding
1. Navigate to BASE_URL
2. Complete login/signup flow
3. Observe onboarding checklist
4. Complete or skip onboarding
5. **Expected calls**: auth/me, onboarding/status, tier-info

#### Journey 2: Dashboard Overview
1. Navigate to /dashboard
2. Wait for all panels to load
3. **Expected calls**: sessions, actions/stats, value-metrics, projects/unassigned-count, context/refresh-check

#### Journey 3: Create & Run Meeting
1. Navigate to /meeting/new
2. Fill problem statement
3. Submit to create session
4. Start deliberation
5. Wait for SSE events (decomposition, personas, contributions)
6. Pause → Resume → Kill flow
7. Extract tasks
8. Export session
9. Create share link
10. **Expected calls**: POST sessions, start, stream (SSE), pause, resume, kill, extract-tasks, export, share

#### Journey 4: Actions Management
1. Navigate to /actions
2. View action list
3. Open action detail
4. Change status (start → complete)
5. Add progress update
6. View/edit reminders
7. Add/remove dependency
8. Update tags
9. View gantt chart
10. **Expected calls**: GET/PATCH actions, updates, reminders, dependencies, tags, gantt

#### Journey 5: Projects Management
1. Navigate to /projects
2. Create new project
3. Open project detail
4. Assign action to project
5. Link session to project
6. View project gantt
7. Open autogen suggestions
8. Delete project
9. **Expected calls**: projects CRUD, assign/unassign actions, link sessions, autogenerate

#### Journey 6: Context Management
1. Navigate to /context
2. View/edit business context
3. Enrich from URL
4. View insights
5. Rate/delete insight
6. View pending updates
7. Approve/dismiss update
8. **Expected calls**: context CRUD, enrich, insights, pending-updates

#### Journey 7: Settings & Billing
1. Navigate to /settings
2. Update preferences
3. Navigate to /settings/billing
4. View plan and usage
5. Click upgrade (don't complete checkout)
6. View email preferences
7. Update retention settings
8. **Expected calls**: preferences, billing/plan, billing/usage, checkout, email-preferences, retention

#### Journey 8: Workspaces
1. Navigate to workspace settings
2. View members
3. Create workspace (if allowed)
4. Update workspace settings
5. View join requests
6. **Expected calls**: workspaces CRUD, members, join-requests

#### Journey 9: Data Analysis (if feature enabled)
1. Navigate to /data
2. Upload CSV dataset
3. Open dataset
4. Run profile
5. Ask question (SSE)
6. Generate chart
7. **Expected calls**: datasets upload, profile, ask (SSE), chart

#### Journey 10: Mentor Chat (if feature enabled)
1. Navigate to mentor chat
2. Select persona
3. Send message (SSE)
4. View conversation history
5. **Expected calls**: mentor/chat (SSE), personas, conversations

#### Journey 11: Admin Panel (if admin)
1. Navigate to /admin
2. View stats
3. View users list
4. View active sessions
5. View waitlist
6. View whitelist
7. **Expected calls**: admin/stats, admin/users, admin/sessions, admin/waitlist, admin/beta-whitelist

#### Journey 12: Public Share
1. Create share link in Journey 3
2. Open incognito/new tab
3. Navigate to share URL
4. **Expected calls**: GET /api/v1/share/{token}

---

## C) Execution (Playwright MCP)

### Execution Protocol

For each journey step:

```
1. Action:
   - Use browser_snapshot to get current state
   - Use browser_click/browser_type/browser_fill_form for interactions
   - Use browser_navigate for page transitions

2. Wait:
   - Use browser_wait_for for expected text/state changes
   - Default timeout: 10s for UI, 30s for SSE operations

3. Capture:
   - After each action: browser_network_requests
   - After navigation: browser_console_messages

4. Assert:
   - Verify expected network calls occurred
   - Verify no console errors (level: error)
   - Verify no 4xx/5xx responses (except expected 4xx like 404 on missing)

5. Record:
   - Log: step, endpoint hit, status, duration
   - Flag: any unexpected errors
```

### Selector Strategy
- Prefer: `[data-testid="..."]` if available
- Fallback: role selectors (`button[name="..."]`, `link[name="..."]`)
- Text selectors: `text="Submit"`, `text="Create"`
- Avoid: CSS class selectors, complex XPath

### SSE Handling
For SSE endpoints (stream, ask, chat):
1. Trigger the action that starts SSE
2. Use browser_wait_for with text indicating completion
3. Capture network requests to verify SSE connection
4. Record events received (via console or UI state)

### Error Recovery
- If login required: Execute Journey 1 first
- If element not found: Take screenshot, log error, continue
- If endpoint 500: Log full request/response, continue
- If timeout: Log, retry once, then flag and continue

---

## D) Validation

### Coverage Tracking

Maintain two lists:
1. **Hit endpoints**: Endpoints successfully triggered via UI
2. **Missed endpoints**: Endpoints not triggered

### Severity Classification

**P0 - Critical**:
- Any 5xx error on core flows (create/view meeting, actions)
- Auth endpoints failing
- Console errors with "crash", "fatal", "unhandled"

**P1 - High**:
- 4xx errors (except expected 401/403/404)
- SSE connection failures
- Core feature unavailable

**P2 - Medium**:
- Slow requests (>5s)
- Non-critical endpoint failures
- Console warnings

**P3 - Low**:
- Slow requests (2-5s)
- Minor UI inconsistencies

### Permission Boundary Validation
For non-admin users, verify:
- No `/api/admin/*` calls succeed from browser
- No technical events (like `phase_cost_breakdown`) visible in UI
- Session actions limited to owned sessions

---

## E) Output Files

### 1. `_API_COVERAGE_REPORT.md`

```markdown
# API Coverage Report
Generated: {timestamp}

## Summary
- Total endpoints: {N}
- Endpoints with UI callers: {N}
- Endpoints without UI callers: {N}
- Hit in this run: {N}
- Missed (should have UI caller): {N}

## Coverage by Category
| Category | Total | Hit | Missed | % |
|----------|-------|-----|--------|---|
| Sessions | X | X | X | X% |
| Actions | X | X | X | X% |
| ... | ... | ... | ... | ... |

## Failures

### P0 - Critical
{list failures with reproduction steps}

### P1 - High
{list failures}

### P2 - Medium
{list failures}

## Console Errors
{list unique console errors with page/step}

## Slow Requests (>2s)
| Endpoint | Duration | Step |
|----------|----------|------|
| ... | ... | ... |

## Endpoints Without UI Callers
{list with reason: internal, webhook, ssr-only, etc.}
```

### 2. `_API_COVERAGE_MATRIX.md`

```markdown
# API Coverage Matrix

## Legend
- [x] Hit successfully
- [ ] Not hit
- [S] Server-only (SSR)
- [I] Internal (no UI caller)
- [!] Error during hit

## Sessions
- [x] POST /api/v1/sessions - Journey 3, Step 3
- [x] GET /api/v1/sessions - Journey 2, Step 1
- [x] GET /api/v1/sessions/{id} - Journey 3, Step 4
...

## Actions
- [x] GET /api/v1/actions - Journey 4, Step 1
...

## (continue for all categories)
```

---

## Execution Checklist

Before running:
- [ ] App running at localhost:5173 and localhost:8000
- [ ] Test credentials available or signup possible
- [ ] Playwright MCP tools available

During run:
- [ ] Execute journeys 1-12 in order
- [ ] Capture all network requests
- [ ] Log console errors
- [ ] Track endpoint coverage

After run:
- [ ] Generate _API_COVERAGE_REPORT.md
- [ ] Generate _API_COVERAGE_MATRIX.md
- [ ] No application code modified

---

## Notes

### Endpoints Marked "No UI Caller"
These endpoints are intentionally server-only or triggered by external systems:
- Health probes: `/api/health/*` (k8s)
- Webhooks: `/api/v1/billing/webhook` (Stripe)
- CSP reports: `/api/v1/csp-report` (browser)
- Analytics: `/api/v1/analytics/*` (JS tracker)
- Client metrics: `/api/v1/metrics/client` (error tracker)
- Email unsubscribe: `/api/v1/email/unsubscribe` (email links)
- Admin SSR: `/api/admin/*` (server-rendered pages)

### SSE Endpoints
These use Server-Sent Events:
- `/api/v1/sessions/{id}/stream` - Meeting events
- `POST /api/v1/datasets/{id}/ask` - Dataset Q&A
- `POST /api/v1/mentor/chat` - Mentor responses
- `POST /api/v1/analysis/ask` - Analysis responses

### Rate Limits
Be aware of rate limits:
- Session creation: 10/hour
- Feedback: 5/hour
- General API: No explicit limits

---

**END OF PROMPT**
