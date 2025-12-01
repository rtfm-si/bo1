## BACKLOG

feature request
implement some kind of 'gated' features, where (user a) can see page 123 but user b cant

# Activate the venv

source .venv/bin/activate

ssh root@139.59.201.65

db tests users etc

add business context page
& research competition

new meeting
(suggest q's based on bus context - CTA to add)

'please wait' message ui is inconsistent

dont need to display' discussion_quality_status' events in the main meeting ui in left panel

meetings seem to disappear from the dashboard - why?

some kind of 'simple' kanban board for actions

'mentor mode' - speak with an expert directly in a chat (like chatgpt) but has business and problem context and actions etc etc

full report:
rounds, minutes, experts = replace with experts and why?
full synthesis missing
needs the exec summary and recommendation right after problem statement

opus:
look for legacy / backwards compatibility / fallback and simplify, we dont need this - no live customers
look for persistence gaps - we should be storing all outputs we produce for end users (meetings etc) in the db
look for optimisations, efficiencies - redundant conversions between pydantic and dicts etc. or simplify this via an reuseable 'autoconverter'?
look for libraries and depedencies providing the same / conflicting capability
look for front end and back end issues

need a counter for:
topics explored
research performed
risks mitigated
challenges resolved
options discussed
etc...

inject business context

add delete user to admin
add 'lock accohnt' to admin

is graph too complicated
simpplfy?
problems decomposed too much?
sub problems must be direct and relevant to solving problem

summarization needs to work better
sub problems fail and summary generated

'still working' messages are crap and inconsistent

still displaying multiple 'completed' messages

you are running a virtual meeting, but using all of the existing code. dont use actual LLM calls, just use your knwledge of the inputs and outputs and trace the graph, vs what gets displayed in the UI. look for :

- duplicate responses where we repeat the same event to the UI (e.g. multiple sub problem completed messages)
- sub problems failing, but the summary tab is produced
- summary being produced with only some of the sub problems complete. all sub problems are required answering before summary
- summarization used effectively, and whether each message is being summarizes appropriately, and being passed forward into the next stage of the meeting efficiently, and appropriately
- is the graph too complicated? should we simplify this? are we calling for research, challenging, making sure we dont repeat, and drift etc?
- are we generating / decomposing into too many sub problems? are the sub problems relevant and required for asnwering the main problem?
- all the 'still working...' messages seem to be not triggered, or triggered too late, or triggered inconsistently, or formatted/displayed inconsistently. they should trigger immediately after the previous message and display more prominantly (but not over the top of, like a pop up) - mayeb in a sticky somewhere?

design a test (or chain of tests) that confirms a meeting can complete e2e.

add experts that are able to contribute to meetings at a more informal level, more sole trader level
would adding 'business style', or 'revenue', customers, employees etc etc help?

we should do more proactive research if the queston is ever 'this' vs 'that', so we can consider demand, costs, risks etc etc

we use deliberation, meeting, discussion

we should standardise the language throught the app: app taxonomy

remove the --- from the meeting complete blocks (crerates a faint line)

tidy up the action card
