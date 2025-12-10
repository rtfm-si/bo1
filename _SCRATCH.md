click and drag on gantt clicks into action. only click and release should click in, click and drag should not.
are the dates persisted on drag?
actions / meetings should be able top be assigned to projects, with dependencies
actions added to report should show the full detail of the actions
clicking back on action should take you back to kanban / gantt - whatveer was previous
can / should we better colour code the gantt chart? projects/ status
can we track delays and early start / finish etc?
can / should we have some way to measure proress on actions? percent, or points, or status? action states need expanding
test suites seem to take a LONG time - how can we better optimise them?

do we need pragmatist expert?

insights need to be translated into something a bit better

For public Google Sheets access via API key, you need:

1. Enable Google Sheets API - Yes, this is required
2. Google Drive API - Not needed for reading public sheets via API key

Steps:

1. Go to https://console.cloud.google.com
2. Create/select a project
3. Go to APIs & Services > Library
4. Search "Google Sheets API" → Enable it
5. Go to APIs & Services > Credentials
6. Click Create Credentials > API Key
7. (Optional but recommended) Restrict the key:

   - Application restrictions: HTTP referrers or IP addresses
   - API restrictions: Google Sheets API only

Then add to your .env:
GOOGLE_API_KEY=your_api_key_here

Note: This only works for sheets set to "Anyone with the link can view". Private sheets would require OAuth (user consent flow), which
we deferred to P2.

check entire app for svelte 5
