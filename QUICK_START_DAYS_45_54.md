# Quick Start: Days 45-54 Implementation

**Google OAuth + Action Tracking Lite**

---

## Day 45-46: Google OAuth Backend (2 days)

### Setup
```bash
# Verify Supabase GoTrue running
docker-compose ps | grep supabase-auth
docker logs bo1-supabase-auth
curl http://localhost:9999/health

# Check .env
grep GOOGLE_OAUTH .env
grep SUPABASE .env
```

### Files to Create
1. **backend/api/auth.py** - OAuth endpoints
   - `GET /api/auth/google` - Redirect to Google
   - `POST /api/auth/callback` - Exchange code for JWT
   - `POST /api/auth/refresh` - Refresh token
   - `POST /api/auth/signout` - Clear cookies

2. **tests/test_auth_oauth.py** - Test suite

### Files to Update
- **backend/api/main.py** - Register auth router
- **backend/api/middleware/auth.py** - Remove `test_user_1` fallback

### Testing
```bash
# Unit tests
pytest tests/test_auth_oauth.py -v

# Manual test
curl http://localhost:8000/api/auth/google
# Should redirect to Google OAuth
```

---

## Day 47-48: Google OAuth Frontend (2 days)

### Files to Create
1. **frontend/src/routes/(auth)/login/+page.svelte**
   - "Sign in with Google" button
   - Redirects to `/api/auth/google`

2. **frontend/src/routes/(auth)/callback/+page.svelte**
   - Handles OAuth callback
   - Exchanges code for JWT
   - Stores in httpOnly cookies

3. **frontend/src/lib/stores/auth.ts**
   - Auth state management
   - `checkAuth()` function
   - `signOut()` function

### Files to Update
- **frontend/src/routes/(app)/+layout.svelte** - Protected route middleware

### Testing
```bash
# Frontend dev server
cd frontend
npm run dev

# Manual test
# 1. Visit http://localhost:3000/login
# 2. Click "Sign in with Google"
# 3. Verify redirect to Google
# 4. Complete OAuth flow
# 5. Verify redirect to /sessions
# 6. Check cookies (access_token, refresh_token)
```

---

## Day 50-51: Action Tracking Backend (2 days)

### Database Migration
```bash
# Create migration (already generated)
alembic upgrade head

# Verify table created
psql -U postgres -d bo1 -c "\d actions"
```

### Files to Create
1. **bo1/models/actions.py** - Pydantic models
   - `ActionBase`
   - `ActionCreate`
   - `Action`
   - `ExtractedAction`
   - `ActionExtractRequest`
   - `ActionExtractResponse`

2. **backend/api/actions.py** - API endpoints
   - `POST /api/actions/extract` - AI extraction
   - `POST /api/actions` - Save actions
   - `GET /api/actions` - List user actions
   - `DELETE /api/actions/{id}` - Delete action
   - `PUT /api/actions/{id}` - Update action

3. **tests/test_actions_api.py** - Test suite

### Files to Update
- **backend/api/main.py** - Register actions router

### Testing
```bash
# Unit tests
pytest tests/test_actions_api.py -v

# Manual test
curl -X POST http://localhost:8000/api/actions/extract \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>"}'
```

---

## Day 52-53: Action Tracking Frontend (2 days)

### Files to Create
1. **frontend/src/lib/components/ActionExtractor.svelte**
   - Displays AI-extracted actions
   - Edit descriptions, set target dates
   - Add/remove actions
   - Save or skip flow

2. **frontend/src/routes/(app)/actions/+page.svelte**
   - Actions dashboard
   - Filters: All, Upcoming, Overdue
   - Sort by target date
   - Delete actions

3. **frontend/src/lib/types.ts** - TypeScript types
   - `ExtractedAction`
   - `Action`

### Files to Update
- **frontend/src/routes/(app)/sessions/[id]/+page.svelte**
  - Show `ActionExtractor` after synthesis

### Testing
```bash
# Frontend dev server
cd frontend
npm run dev

# Manual test
# 1. Complete a deliberation
# 2. Verify action extractor appears after synthesis
# 3. Edit actions, set target dates
# 4. Click "Save Actions"
# 5. Visit /actions
# 6. Verify actions listed
# 7. Test filters (upcoming, overdue)
# 8. Delete action
```

---

## Day 54: Integration + Testing (1 day)

### E2E Tests
**File**: `tests/e2e/test_actions_lite.py`

```bash
# Run E2E tests
pytest tests/e2e/test_actions_lite.py -v
```

### Manual Testing Checklist
- [ ] OAuth: Sign in with Google
- [ ] OAuth: Protected routes redirect to /login
- [ ] OAuth: Sign out clears cookies
- [ ] Actions: Extraction works (3-7 actions)
- [ ] Actions: Edit descriptions
- [ ] Actions: Set target dates
- [ ] Actions: Add/remove actions
- [ ] Actions: Save actions
- [ ] Actions: Dashboard loads
- [ ] Actions: Filters work
- [ ] Actions: Delete action
- [ ] Actions: Mobile responsive

### Performance Tests
```bash
# Load 100 actions, verify dashboard fast
# Check for N+1 queries
# Verify action extraction cost ~$0.002
```

### Documentation
- [ ] Update `docs/ACTIONS_LITE.md`
- [ ] Update roadmap progress (24/62 → 62/62)
- [ ] Commit changes

---

## Quick Reference

### Environment Variables (.env)
```bash
# OAuth
ENABLE_SUPABASE_AUTH=true
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=490598945509-...
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
SUPABASE_URL=http://localhost:9999
SUPABASE_JWT_SECRET=<secret>

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bo1
```

### Database Schema (actions table)
```sql
CREATE TABLE actions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  session_id UUID REFERENCES sessions(id),
  description TEXT NOT NULL,
  target_date DATE NOT NULL,
  priority INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

### API Endpoints

**Auth**:
- `GET /api/auth/google` - OAuth redirect
- `POST /api/auth/callback` - Exchange code for JWT
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/signout` - Sign out

**Actions**:
- `POST /api/actions/extract` - Extract from synthesis
- `POST /api/actions` - Save actions
- `GET /api/actions` - List user actions
- `DELETE /api/actions/{id}` - Delete action
- `PUT /api/actions/{id}` - Update action

### Frontend Routes

**Auth**:
- `/login` - Sign-in page
- `/auth/callback` - OAuth callback

**Actions**:
- `/actions` - Actions dashboard
- `/sessions/{id}` - Session page (shows ActionExtractor after synthesis)

---

## Troubleshooting

### OAuth "Google OAuth not configured"
```bash
# Check .env
grep GOOGLE_OAUTH .env

# Restart backend
docker-compose restart api
```

### OAuth "Failed to exchange authorization code"
```bash
# Check GoTrue logs
docker logs bo1-supabase-auth

# Verify redirect URI matches Google console
# Development: http://localhost:9999/callback
```

### Actions "Session has no synthesis report yet"
```bash
# Verify synthesis exists
psql -U postgres -d bo1 -c "SELECT id, synthesis FROM sessions WHERE id = '<session_id>';"

# Complete deliberation first
```

### Actions extraction fails
```bash
# Check LLM client works
pytest tests/test_llm_client.py -v

# Check Anthropic API key
grep ANTHROPIC_API_KEY .env

# Check synthesis content
# Action extraction requires synthesis with "Next Steps" section
```

---

## Cost Tracking

| Item | Cost |
|------|------|
| OAuth infrastructure | $0 (self-hosted) |
| Action extraction (Haiku 4.5) | ~$0.002/deliberation |
| Storage (100 bytes/action) | Negligible |
| **Total per 100 users** | **~$1/month** |

---

## Success Metrics

### Day 48 (OAuth)
- ✅ 100% users can sign in with Google
- ✅ JWT stored in httpOnly cookies
- ✅ Protected routes redirect to /login
- ✅ All tests pass

### Day 54 (Actions)
- ✅ 100% deliberations can extract actions
- ✅ Users can edit/save/delete actions
- ✅ Dashboard loads <500ms (100 actions)
- ✅ All E2E tests pass

---

## Next Steps After Day 54

**Week 8-9** (Days 55-63): Stripe Payments + GDPR
- Stripe checkout flow
- Rate limiting per tier
- GDPR user rights (data export, deletion)

**Implementation Docs**:
- Full details: `zzz_project/detail/GOOGLE_OAUTH_IMPLEMENTATION.md`
- Full details: `zzz_project/detail/ACTION_TRACKING_LITE_IMPLEMENTATION.md`
- Migration: `migrations/versions/2f7e9d4c8b1a_add_actions_lite.py`
