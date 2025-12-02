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

SEO

meeting image > should be a carousel type animation
card with 'problem statement' pops up
next is 'experts discuss...'
final is the pdf report output view?

could 'expert panel assembled' be columns instead of rows (should always be between 2 min and 5 max)?

need to check the 'clarify' options - dont seem to be getting triggered. write responses to 'business context' timestamped

how robust is our security on prod regarding users creating free accounts and spamming 'start meeting'?

determine whatand inject business context to problems

add delete user to admin
add admin ability to 'lock account' and 'unlock account'

add experts that are able to contribute to meetings at a more informal level, more sole trader level
would adding 'business style', or 'revenue', customers, employees etc etc help?

we should do more proactive research if the queston is ever 'this' vs 'that', so we can consider demand, costs, risks etc etc
I think we should be triggering research a bit more frequently than we are doing? - should a problem like this:
Should we raise Series A now or wait 6 months, given current metrics, market conditions, and realistic improvement potentiall perform research into current market conditions?

actions should be 'trackable' and ability to 'replan' - what went wrong,

onboarding flow

A. Company Identity (Tiny Input → Big Expansion)

Company name (input)

Website URL (input → auto-crawl + enrich)

Extract: industry, product categories, pricing pages, positioning, tone, brand maturity, SEO structure, tech stack (Wappalyzer style)

B. Business Stage & Priority

Just a couple of lightweight dropdowns:

Stage: idea → early → growing → scaling

Primary objective: acquire customers / improve retention / raise capital / launch product / reduce costs / etc.

prompt to add after first q completion and 'are these details correct...' every n months? 2. IMPORTANT — High value, but optional for simplicity

These add measurable precision to decisions but shouldn’t block usage.

A. Target Customer & Market

Target customer profile

Geography or market served

Industry niche (if unclear from website)

B. Business Performance Signals

Small, non-financial indicators:

Traffic range (self-reported or scraped estimates)

Monthly active users (rough buckets)

Revenue stage (pre-revenue / <£10k MRR / etc.)

C. Product Snapshot

Main product or service

Value proposition (can be AI-extracted from homepage)

D. Team Context

Solo founder? small team? contractors?
This influences advice quality (e.g., feasibility of actions).

E. Constraints

Budget constraints

Time constraints

Regulatory concerns (if relevant)

Enrich from the website:

Extract products, value prop, pricing, positioning, tone

Detect business model (SaaS, marketplace, agency, etc.)

Identify competitors

Identify ICP

Extract keywords to detect market category

Pull current market trends via external search APIs

Identify missing pieces relevant to the decision
