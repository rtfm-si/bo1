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
etc...

research best practice for our meeting flow management: facilitator steers and direct the meetings, with checks for novelty, consensus, challenge, drift etc. we utilise research tools (brave / tavily), embeddings (voyage ai), summarizers (anthropic), 'judges' on return content for accuracy and relevance (anthropic) etc. we use parallelisation wherever possible.
we want to ensure that experts produce the absolue best content, in as few steps as possible - the apex of cost vs quality - maybe edging towards slightly higher cost for better quality.

how well does our current implementation work? how could it be improved. what gaps do we have? what doesnt work well? what are we missing?

inject business context
