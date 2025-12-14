settings/billing
plan and usage - wrong prices and features.

add 'meetings' to 'board' drop down
move 'business context' from settings to its own page and seperate drop down
move 'intelligence' from settings to its own page and a 'reports' drop down

remove meeting cost calculator from dashboard

failed to submit clarification questions
[vite] connecting... client:733:9
[vite] connected. client:827:12
[AppLayout] Checking authentication... debug.ts:4:13
[Auth] Initializing auth... debug.ts:4:13
[Auth] Checking if session exists... debug.ts:4:13
[Auth] Session exists: true debug.ts:4:13
[Auth] Fetching user info from /api/v1/auth/me... debug.ts:4:13
[Auth] /api/v1/auth/me response status: 200 debug.ts:4:13
[Auth] User data:
Object { id: "c04ea5f4-e6f0-460c-bb48-66cdf6245bb4", user_id: "c04ea5f4-e6f0-460c-bb48-66cdf6245bb4", email: "si@boardof.one", auth_provider: "google", subscription_tier: "free", is_admin: true, session_handle: "8a484508-d36f-498f-b02a-db5a90611865" }
debug.ts:4:13
[AppLayout] Auth check complete. Authenticated: true debug.ts:4:13
[Workspace] Loading workspaces... debug.ts:4:13
[Auth] Authentication successful! debug.ts:4:13
[Dashboard] Loading sessions for user: si@boardof.one debug.ts:4:13
XHRGET
http://localhost:8000/api/v1/user/cost-calculator-defaults
[HTTP/1.1 404 Not Found 114ms]

[OperationTracker] Failed operation: api:GET:/api/v1/user/cost-calculator-defaults Not Found
Object { endpoint: "/api/v1/user/cost-calculator-defaults", method: "GET", status: 404 }
operation-tracker.ts:172:15
[Workspace] Loaded 0 workspaces debug.ts:4:13
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/lib/components/ui/Spinner.svelte client:810:29
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/lib/components/ui/Spinner.svelte client:810:29
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/lib/components/ui/Button.svelte client:810:29
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/lib/components/ui/Button.svelte client:810:29
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/app.css client:810:29
XHRGET
http://localhost:8000/api/v1/projects/unassigned-count
[HTTP/1.1 500 Internal Server Error 41ms]

[OperationTracker] Failed operation: api:GET:/api/v1/projects/unassigned-count An unexpected error occurred
Object { endpoint: "/api/v1/projects/unassigned-count", method: "GET", status: 500 }
operation-tracker.ts:172:15
Failed to load unassigned count: ApiClientError: An unexpected error occurred
ApiClientError client.ts:529
fetch client.ts:590
getUnassignedCount client.ts:1358
loadUnassignedCount +page.svelte:37
\_page +page.svelte:32
untrack runtime.js:704
onMount index-client.js:100
update_reaction runtime.js:256
update_effect runtime.js:431
flush_queued_effects batch.js:705
process batch.js:194
flush_effects batch.js:648
flush batch.js:343
ensure batch.js:524
run_all utils.js:45
run_micro_tasks task.js:10
queue_micro_task task.js:28
queue_micro_task task.js:19
enqueue batch.js:534
ensure batch.js:518
internal_set sources.js:186
set sources.js:165
set legacy-client.js:109
<anonymous> legacy-client.js:147
$set legacy-client.js:157
navigate client.js:1739
\_start_router client.js:2571
\_start_router client.js:2462
start client.js:372
async* dashboard:7621
promise callback* dashboard:7620
+page.svelte:171:12
[vite] hot updated: /src/app.css client:810:29
[vite] hot updated: /src/app.css client:810:29
[OperationTracker] Slow operation: api:POST:/api/v1/competitors/6949924a-f4cf-4695-a9db-503ac6134d4c/enrich took 4674ms
Object { endpoint: "/api/v1/competitors/6949924a-f4cf-4695-a9db-503ac6134d4c/enrich", method: "POST", status: 200 }
client.js:3208:15
[Dashboard] Loading sessions for user: si@boardof.one debug.ts:4:13
XHRGET
http://localhost:8000/api/v1/user/cost-calculator-defaults
[HTTP/1.1 404 Not Found 61ms]

[OperationTracker] Failed operation: api:GET:/api/v1/user/cost-calculator-defaults Not Found
Object { endpoint: "/api/v1/user/cost-calculator-defaults", method: "GET", status: 404 }
operation-tracker.ts:172:15
[DecisionMetrics] No convergence events yet, count: 0 DecisionMetrics.svelte:130:13
[Events] Loading historical events... +page.svelte:411:12
[Events] Loaded 1 historical events +page.svelte:415:12
[Events] Session and history loaded, checking session status... +page.svelte:576:13
[SSE] Connection established sseConnection.svelte.ts:113:13
[WORKING STATUS] Breaking down your decision into key areas... undefined sseConnection.svelte.ts:61:13
[DecisionMetrics] No convergence events yet, count: 0 DecisionMetrics.svelte:130:13
[TabBuild] Decomposition event:
Object { subProblemsCount: 3 }
debug.ts:14:13
[TabBuild] Building tabs for 3 sub-problems debug.ts:14:13
[TabBuild] Sub-problem 0:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 1:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 2:
Object { totalEvents: 0 }
debug.ts:14:13
[DecisionMetrics] No convergence events yet, count: 0 3 DecisionMetrics.svelte:130:13
[TabBuild] Decomposition event:
Object { subProblemsCount: 3 }
debug.ts:14:13
[TabBuild] Building tabs for 3 sub-problems debug.ts:14:13
[TabBuild] Sub-problem 0:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 1:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 2:
Object { totalEvents: 0 }
debug.ts:14:13
[DecisionMetrics] No convergence events yet, count: 0 DecisionMetrics.svelte:130:13
XHRPOST
http://localhost:8000/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/clarifications
CORS Missing Allow Origin

Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at http://localhost:8000/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/clarifications. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 403.
Failed to submit clarifications: TypeError: NetworkError when attempting to fetch resource. ClarificationForm.svelte:80:12
XHRPOST
http://localhost:8000/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/clarifications
CORS Missing Allow Origin

Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at http://localhost:8000/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/clarifications. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 403.
Failed to submit clarifications: TypeError: NetworkError when attempting to fetch resource. ClarificationForm.svelte:80:12

end meeting early:
[vite] connecting... client:733:9
[vite] connected. client:827:12
[AppLayout] Checking authentication... debug.ts:4:13
[Auth] Initializing auth... debug.ts:4:13
[Auth] Checking if session exists... debug.ts:4:13
[Auth] Session exists: true debug.ts:4:13
[Auth] Fetching user info from /api/v1/auth/me... debug.ts:4:13
[Auth] /api/v1/auth/me response status: 200 debug.ts:4:13
[Auth] User data:
Object { id: "c04ea5f4-e6f0-460c-bb48-66cdf6245bb4", user_id: "c04ea5f4-e6f0-460c-bb48-66cdf6245bb4", email: "si@boardof.one", auth_provider: "supertokens", subscription_tier: "free", is_admin: true, session_handle: "8a484508-d36f-498f-b02a-db5a90611865" }
debug.ts:4:13
[AppLayout] Auth check complete. Authenticated: true debug.ts:4:13
[Workspace] Loading workspaces... debug.ts:4:13
[Auth] Authentication successful! debug.ts:4:13
[Workspace] Loaded 0 workspaces debug.ts:4:13
[DecisionMetrics] No convergence events yet, count: 0 DecisionMetrics.svelte:130:13
[Events] Loading historical events... +page.svelte:411:12
[Events] Loaded 6 historical events +page.svelte:415:12
[DecisionMetrics] No convergence events yet, count: 0 DecisionMetrics.svelte:130:13
[TabBuild] Decomposition event:
Object { subProblemsCount: 3 }
debug.ts:14:13
[TabBuild] Building tabs for 3 sub-problems debug.ts:14:13
[TabBuild] Sub-problem 0:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 1:
Object { totalEvents: 0 }
debug.ts:14:13
[TabBuild] Sub-problem 2:
Object { totalEvents: 0 }
debug.ts:14:13
[DecisionMetrics] No convergence events yet, count: 0 2 DecisionMetrics.svelte:130:13
[Events] Session and history loaded, checking session status... +page.svelte:576:13
[Events] Session is paused, skipping SSE connection +page.svelte:580:14
XHRPOST
http://localhost:8000/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/terminate
[HTTP/1.1 422 Unprocessable Entity 11ms]

[OperationTracker] Failed operation: api:POST:/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/terminate [object Object]
Object { endpoint: "/api/v1/sessions/bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a/terminate", method: "POST", status: 422 }
operation-tracker.ts:172:15
Failed to terminate session: ApiClientError: [object Object]
ApiClientError client.ts:529
fetch client.ts:590
post client.ts:621
terminateSession client.ts:818
handleSubmit TerminationModal.svelte:58
apply events.js:337
\_\_click Button.svelte:61
handle_event_propagation events.js:261
event_handle render.js:179
\_mount render.js:194
hydrate render.js:117
Svelte4Component legacy-client.js:115
<anonymous> legacy-client.js:54
initialize client.js:587
\_hydrate client.js:2855
start client.js:361
async* bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a:7637
promise callback* bo1_d30c7db0-5dd7-4684-ad95-0bed9281c16a:7636
TerminationModal.svelte:96:12
