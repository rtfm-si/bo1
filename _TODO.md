The root cause of the 429s is likely the global IP rate limiter (500/minute) blocking requests when admin pages fire 10-15 parallel API calls on load. Admin endpoints already require API key authentication, so the global IP limit is redundant for these routes.

perhaps we are firing too may appi calls? can we simplify this to an 'admin page' call that uses a single api call?
