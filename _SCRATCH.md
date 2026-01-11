get new bank account for sico software
get companies house id sorted
get vat number
change business code on companies house

grafana logs: value A
umami funnels etc

refactor mentor routes to 'advisor'

advsor/analyze - too much space given over to data load, and not enough to actual datasets
we should allow 'folders' for datasets, with names & tags etc

analyze: what data do i need = error:
XHRGET
https://boardof.one/api/v1/objectives/data-requirements
[HTTP/2 401 34ms]

XHRGET
https://boardof.one/api/v1/objectives/0/data-requirements
[HTTP/2 500 52ms]

Failed to load data requirements: ApiClientError: An unexpected error occurred
Immutable 13
async* https://boardof.one/advisor/analyze:120
promise callback* https://boardof.one/advisor/analyze:119
35.l1XIzzRC.js:5:16309

advsor/grow = too cramped. 4 cards need streamlining
analyze user submitted words, or 'go get the best topics for me...'
should we go straight to generated article, with revision options? think so...

context:
remove - explore more context

context> metrics - should have a 'help me calculate' (see q&a )
need a 'help me calculate this...' e.g. churn rate. ask user questions to build from ground up:
Q: whats churn rate?
A: i dont know...
Q: how many customers did you start last month?
A: 200
Q: how many customers left last month
A: 10
=10 / 200 = 5%
etc...
user clicks a buttin and we populate all the metrics with q&a dialog. start with basic building blocjs and build up. store every answer as insight

context > insights should be mapped to context>metrics wherever possible

reports> competitors needs work - competitors selected are too general, and not specific enough. rarely have any / good insight associated with them. enrich doesnt seem to do anything. enrich should be automatic

industry benchmarks dont align to the metrics we choose as being 'best' for the business. need to check that business metrics (focus metrics) are best for business, indstry and current objective

market trends fails: XHRPOST
https://boardof.one/api/v1/context/trends/summary/refresh
[HTTP/2 500 50ms]

live market trends are just news stories - we should extract and summarise the articles
