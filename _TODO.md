admin user impersonation needs some way of accessing via admin

admin/blog page needs a link from the admin page

XHRGET
https://boardof.one/api/admin/blog/posts
[HTTP/2 429 22ms]

XHRGET
https://boardof.one/api/admin/impersonate/status
[HTTP/2 429 22ms]

XHRGET
https://boardof.one/api/admin/blog/posts?status=scheduled
[HTTP/2 429 21ms]

XHRGET
https://boardof.one/api/admin/blog/posts?status=published
[HTTP/2 429 25ms]

XHRGET
https://boardof.one/api/admin/blog/posts?status=draft
[HTTP/2 429 22ms]

trying to create a blog post generates: Invalid input: Blog generation returned invalid JSON format

status.boardof.one = 502 bad gateway

clicking delete on an action doesnt do anything
XHRGET
https://boardof.one/api/v1/actions/15293395-9625-4a25-b5d0-acb6cf12a518/reminder-settings
[HTTP/2 404 36ms]

Failed to load reminder settings: ApiClientError: Action not found
Immutable 56
async* https://boardof.one/actions:122
promise callback* https://boardof.one/actions:121
10.bCnn3fiQ.js:1:29563
