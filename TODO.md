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

need a counter for:
topics explored
research performed
risks mitigated
challenges resolved
etc...

https://boardof.one/meeting/bo1_69ffd4f5-faf8-41c3-8653-1ea71d011a95

experts arent showing on sub problem start
the sub problem conclusion is garbled ? only shown on dev
costs displayed
'next speaker...' type messages are still not appearing
discussion qulaity doesnt update across sub problems- just shows 'complete' after 1st sub problem
do we fully explore 6 rounds always, or can we stop early?
we should extract the things the subproblem wants discussion so its focussed and targetted.
facilitator calls on specific experts to answer / contribute based on their expertise?
final sub problem still no 'completion' or synthesis summary

AFTER REFRESH:
sse errors (do we need to try and reconnect to SSE if the stream has ended?)
http://localhost:5173/meeting/bo1_2f1df879-b60c-40a8-ab6e-312f9d80fb04
shows discussion_quality_status (hide these events)
sub problem 1 shows the decomposition(this should be on the summary tab, with hyperlink to the tab)

each tab shows:
meeting complete summary for the sub problem AND
a sub problem complete (seems full text or something?) AND
actions from all sub problems

needs to be faster
needs to be more 'to the point', focussed
the more a problem is decomposed
