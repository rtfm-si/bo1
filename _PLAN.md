# Plan: [AUTH][P0] Fix Google Social Login for Existing Email Users

## Summary

- Enable SuperTokens AccountLinking recipe to automatically link OAuth providers with existing email accounts
- Configure automatic linking for verified emails from trusted providers (Google, LinkedIn, GitHub)
- Add logging to diagnose linking failures
- Test with existing email user signing in via Google

## Root Cause

User `info@seilich.co.uk` first registered with email/password. When attempting Google OAuth:
- SuperTokens creates a **separate** user for the Google identity
- Without AccountLinking, same-email accounts from different providers are NOT linked
- This causes auth failures or duplicate accounts

## Implementation Steps

1. **Add AccountLinking recipe to backend** - `backend/api/supertokens_config.py`
   - Import `accountlinking` recipe from `supertokens_python.recipe`
   - Add to recipe list in `init_supertokens()`
   - Configure `should_do_automatic_account_linking` callback to auto-link verified emails

2. **Configure linking policy** - Same file
   - Auto-link when: email verified AND provider is Google/LinkedIn/GitHub
   - Do NOT link: unverified emails (security)
   - Log linking attempts for audit trail

3. **Add EmailVerification recipe** - Required dependency for AccountLinking
   - SuperTokens AccountLinking requires EmailVerification recipe
   - Configure to mark OAuth provider emails as pre-verified (Google verifies emails)

4. **Update user sync logic** - `override_thirdparty_functions`
   - Handle `AccountLinkingUserNotAllowed` result type
   - Log when linking fails due to policy

5. **Add unit tests** - `tests/api/test_account_linking.py`
   - Test: email user + Google OAuth → same user_id
   - Test: unverified email → no linking
   - Test: different email → separate user

## Tests

- Unit tests:
  - `test_google_links_to_existing_email_user` - existing email user signs in with Google, gets same user_id
  - `test_new_google_user_creates_account` - new email creates fresh account
  - `test_unverified_provider_not_linked` - unverified emails don't auto-link

- Manual validation:
  - Sign up with email@example.com via email/password
  - Try Google OAuth with same email → should link, same user_id
  - Verify user data (subscriptions, workspaces) preserved

## Dependencies & Risks

- Dependencies:
  - SuperTokens Core 10.x+ (already on 10.1.4)
  - `supertokens-python` package supports AccountLinking

- Risks:
  - Existing duplicate accounts: may need admin script to merge
  - Session invalidation: existing sessions should continue working
  - Email verification state: OAuth emails considered verified by provider
