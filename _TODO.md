why does api container take 30s to come online?

header links need ui improving - super squashed on laptop:
get rid of 'new meeting'
remove 'personal' - workspace switching can be done fron settings - most users wont switch workspace

reports dropdown on dashboard should also allow acces to meeting reports

should auto generate projects off back of actions and assign an action to a project
do NOT duplicate projects
dont open a closed project - need to have some way of having 'v2' or whatever

insights in context: looks like we currently record null / empty question responses. we should parse out the relevant cibtext fron the response. dont store null / empty responses ('none'. or 'na/' is a valid response)
we should check in x months if the contexct is still valid - refresh it. volatile metrics, or those affected by actions we are completing should be refreshed / checked on a more regular basis than stable metrics

pretty much every button clicked is broken:
nothing happens, or an error
need to be able to detect this and take action. e2e playwright test as part of CI should write a report to root?

need to increase stability of app, remove fragile operations

it would be nice to add an 'embeddings' page in admin to visualise embeddings in some kind of graphic

add other metrics ad kpis in admin: mentor sessions, data anyisis, projects created, actions created, started completed and cancelled

proactive mentoring: user fails to complete actions, user asks for help with similar thinkg over and over - should proactively develop a plan to help them succeed

improve:
accesibility and modernise uisng shadcn

onboarding new experience using driver.js

> business context
> first meeting
> after meeting > kanban & gantt
> projects
