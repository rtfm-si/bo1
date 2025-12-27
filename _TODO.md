seo errors:
XHRGET
https://boardof.one/api/admin/blog/posts
[HTTP/2 429 20ms]

XHRGET
https://boardof.one/api/admin/blog/posts?status=draft
[HTTP/2 429 20ms]

XHRGET
https://boardof.one/api/admin/blog/posts?status=published
[HTTP/2 429 23ms]

collateral errors:
XHRGET
https://boardof.one/api/v1/seo/assets?limit=100
[HTTP/2 404 358ms]

user ratings:
XHRGET
https://boardof.one/api/v1/admin/ratings/negative?limit=10
[HTTP/2 401 691ms]

XHRGET
https://boardof.one/api/v1/admin/ratings/trend?days=7
[HTTP/2 401 691ms]

XHRGET
https://boardof.one/api/v1/admin/ratings/metrics?days=30
[HTTP/2 401 691ms]

same for admin/feedback

check ALL admin routes for valid 200 responses

local still fails
fix all social logins

'clean' prod server (storage etc). set it up to clean every day?
