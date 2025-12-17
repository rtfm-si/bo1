# Plan: [ANALYTICS][P3] Umami Self-Hosted Analytics Integration

## Summary

- Add Umami container to docker-compose (uses existing `umami` database from init script)
- Create Umami tracking script component for landing page
- Configure via env vars (`PUBLIC_UMAMI_HOST`, `PUBLIC_UMAMI_WEBSITE_ID`)
- Complement existing custom analytics (page-tracker.ts) with richer visitor insights

## Implementation Steps

1. **Add Umami service to docker-compose.yml**
   - Image: `ghcr.io/umami-software/umami:postgresql-latest`
   - Database: use existing `umami` database (init script already creates it)
   - Port: 3002 (avoid conflict with Grafana on 3001)
   - Profile: `analytics` (optional start)

2. **Add env vars to `.env.example` and frontend config**
   - `UMAMI_APP_SECRET` (random 32+ char string)
   - `PUBLIC_UMAMI_HOST` (e.g., `http://localhost:3002`)
   - `PUBLIC_UMAMI_WEBSITE_ID` (set after first login)
   - Frontend: read from `$env/dynamic/public`

3. **Create Umami script component**
   - File: `frontend/src/lib/components/UmamiAnalytics.svelte`
   - Conditionally loads Umami tracking script when `PUBLIC_UMAMI_WEBSITE_ID` is set
   - SSR-safe (only runs in browser)

4. **Add component to root layout**
   - Add `<UmamiAnalytics />` to `frontend/src/routes/+layout.svelte`
   - Loads on all pages (Umami auto-tracks page views)

5. **Update landing page to track custom events**
   - Optional: Use `umami.track()` for specific conversion events
   - Complements existing `trackSignupClick`, `trackWaitlistSubmit`

## Tests

- Unit tests:
  - `UmamiAnalytics.test.ts`: renders nothing when no website ID, renders script when configured

- Manual validation:
  - Start Umami: `docker compose --profile analytics up -d umami`
  - Access Umami UI at `http://localhost:3002`
  - Create website, get website ID
  - Set `PUBLIC_UMAMI_WEBSITE_ID` in frontend `.env`
  - Visit landing page, verify page view tracked in Umami dashboard

## Dependencies & Risks

- Dependencies:
  - Postgres container running (already required)
  - `umami` database created by init script (already exists)

- Risks/edge cases:
  - First-time setup requires manual website creation in Umami UI
  - Website ID must be set after Umami first boot
  - CORS: Umami should allow requests from frontend origin
