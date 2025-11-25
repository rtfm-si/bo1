feature request
implement some kind of 'gated' features, where (user a) can see page 123 but user b cant

# Activate the venv

source .venv/bin/activate

ssh root@139.59.201.65

db tests users etc

left panel:

actions should have a bit of detail next to them, beyond just the title

right panel:

expert contributions in rows PER sub problem (and overall) in columns ?

add business context page
& research competition

http://localhost:5173/meeting/bo1_38113e62-eda5-43e6-afd1-1b20742cf609

after panel assembeld and NO cotributions:
Error Occurred
Fatal ValueError

max_rounds (10) exceeds hard cap of 6 for parallel architecture
This error cannot be recovered. Please check logs and restart the session.

problem decomposition sems random - either a signle simple sub problem or acomplex 4-5 sub problem issue, from the same question. why?

sse connection fails if we refresh mid meeting. sse connection os not robust - it MUST be

[SSE] Connection error: TypeError: Error in input stream retry count: 0 +page.svelte:731:13
[SSE] Retrying in 1000ms... +page.svelte:742:14
SSE reader cancellation failed: TypeError: Error in input stream client.js:3208:15
[Events] Initialization sequence complete +page.svelte:572:13
[vite] connecting... client:733:9
[vite] connected. client:827:12
[App Layout] Checking authentication... +layout.svelte:45:11
[App Layout] Auth loading: true +layout.svelte:49:12
[Auth] Initializing auth... auth.ts:20:11
[Auth] Checking if session exists... auth.ts:23:13
[Auth] Session exists: true auth.ts:25:13
[Auth] Fetching user info from /api/auth/me... auth.ts:27:15
[Auth] /api/auth/me response status: 200 auth.ts:32:15
[Auth] User data:
Object { id: "d8a013d2-55a4-42ee-aa81-4e9c23e4cfe8", user_id: "d8a013d2-55a4-42ee-aa81-4e9c23e4cfe8", email: null, auth_provider: "google", subscription_tier: "free", session_handle: "2baf27b3-61b6-4ccd-bd62-08a274e03672" }
auth.ts:35:17
[App Layout] Auth loading: false +layout.svelte:49:12
[App Layout] Auth check complete. Authenticated: true +layout.svelte:53:13
[App Layout] Authenticated, showing protected content +layout.svelte:62:14
[Auth] Authentication successful! auth.ts:42:17
[Events] Loading historical events... +page.svelte:595:12
[Events] Critical components preloaded +page.svelte:549:96
[Events] Loaded 1 historical events +page.svelte:599:12
[TAB BUILD DEBUG] Decomposition event:
Object { eventData: Proxy, subProblemsCount: 1, subProblems: Proxy }
+page.svelte:1005:12
[TAB BUILD DEBUG] Single sub-problem scenario, not building tabs +page.svelte:1012:13
[Events] Session and history loaded, Svelte tick complete, starting SSE stream... +page.svelte:566:13
XHRGET
http://localhost:5173/api/v1/sessions/bo1_38113e62-eda5-43e6-afd1-1b20742cf609/stream
[HTTP/1.1 404 Not Found 4042ms]

[EVENT INDEX DEBUG]
Object { totalEvents: 1, eventsWithSubIndex: 1, eventsWithoutSubIndex: 0, indexedSubProblems: (1) […], eventsPerSubProblem: (1) […] }
+page.svelte:1204:12
[SSE] Connection error: Error: SSE connection failed: 404 Not Found
connect sse.ts:48
startEventStream +page.svelte:563
\_page +page.svelte:383
\_page +page.svelte:391
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
unsubscribe +layout.svelte:64
set2 index.js:57
initAuth auth.ts:87
\_layout +layout.svelte:20
run utils.js:39
fns lifecycle.js:51
untrack runtime.js:704
init lifecycle.js:51
update_reaction runtime.js:256
update_effect runtime.js:431
flush_queued_effects batch.js:705
process batch.js:194
flush_effects batch.js:648
flush batch.js:343
ensure batch.js:524
run_all utils.js:45
run_micro_tasks task.js:10
flush_tasks task.js:40
flushSync batch.js:585
Svelte4Component legacy-client.js:127
<anonymous> legacy-client.js:54
initialize client.js:587
\_hydrate client.js:2855
start client.js:361
async* bo1_38113e62-eda5-43e6-afd1-1b20742cf609:5020
promise callback* bo1_38113e62-eda5-43e6-afd1-1b20742cf609:5019
retry count: 0 +page.svelte:731:13
[SSE] Retrying in 1000ms... +page.svelte:742:14
[Events] Initialization sequence complete +page.svelte:572:13
XHRGET
http://localhost:5173/api/v1/sessions/bo1_38113e62-eda5-43e6-afd1-1b20742cf609/stream
[HTTP/1.1 404 Not Found 6ms]

[SSE] Connection error: Error: SSE connection failed: 404 Not Found
connect sse.ts:48
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
\_page +page.svelte:383
\_page +page.svelte:391
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
unsubscribe +layout.svelte:64
set2 index.js:57
initAuth auth.ts:87
\_layout +layout.svelte:20
run utils.js:39
fns lifecycle.js:51
untrack runtime.js:704
init lifecycle.js:51
update_reaction runtime.js:256
update_effect runtime.js:431
flush_queued_effects batch.js:705
process batch.js:194
flush_effects batch.js:648
flush batch.js:343
ensure batch.js:524
run_all utils.js:45
run_micro_tasks task.js:10
flush_tasks task.js:40
flushSync batch.js:585
Svelte4Component legacy-client.js:127
<anonymous> legacy-client.js:54
initialize client.js:587
\_hydrate client.js:2855
start client.js:361
async* bo1_38113e62-eda5-43e6-afd1-1b20742cf609:5020
promise callback\* bo1_38113e62-eda5-43e6-afd1-1b20742cf609:5019
retry count: 1 +page.svelte:731:13
[SSE] Retrying in 2000ms... +page.svelte:742:14
XHRGET
http://localhost:5173/api/v1/sessions/bo1_38113e62-eda5-43e6-afd1-1b20742cf609/stream
[HTTP/1.1 404 Not Found 16ms]

[SSE] Connection error: Error: SSE connection failed: 404 Not Found
connect sse.ts:48
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
\_page +page.svelte:383
\_page +page.svelte:391
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
retry count: 2 +page.svelte:731:13
[SSE] Retrying in 4000ms... +page.svelte:742:14
XHRGET
http://localhost:5173/api/v1/sessions/bo1_38113e62-eda5-43e6-afd1-1b20742cf609/stream
[HTTP/1.1 404 Not Found 14ms]

[SSE] Connection error: Error: SSE connection failed: 404 Not Found
connect sse.ts:48
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
onError +page.svelte:550
setTimeout handler\*onError +page.svelte:549
connect sse.ts:88
startEventStream +page.svelte:563
\_page +page.svelte:383
\_page +page.svelte:391
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
retry count: 3 +page.svelte:731:13
[SSE] Max retries reached +page.svelte:751:14
