# Board of One - Cookie Policy & Consent Strategy

## TL;DR

**No "Decline All" button needed.** Current implementation ("Accept All" vs "Essential Only") is GDPR/CCPA compliant and best practice.

---

## Cookies We Use

### Essential Cookies (Always On)
These cookies are necessary for the site to function and don't require consent under GDPR Article 6(1)(f).

| Cookie Name | Purpose | Duration | Can User Disable? |
|------------|---------|----------|-------------------|
| `bo1_cookie_consent` | Stores cookie consent preference | 365 days | No (paradox: need cookie to remember "no cookies") |
| `sb-access-token` | Supabase auth JWT (when auth enabled) | Session | No (can't log in without it) |
| `sb-refresh-token` | Supabase refresh token | 30 days | No (can't stay logged in) |

**Note:** Theme preference is stored in `localStorage`, not cookies.

### Optional Cookies (Require Consent)
These are opt-in only and disabled by default.

| Cookie Type | Purpose | When Enabled |
|------------|---------|--------------|
| Analytics | Usage patterns, performance monitoring | User clicks "Accept All" |

**Analytics Provider:** We'll use privacy-friendly analytics (Plausible or Fathom), NOT Google Analytics.

---

## Why No "Decline All" Button?

### Option 1: Decline All (Rejects Everything) ❌
**Problems:**
- Users can't log in (need auth cookies)
- Banner shows on every page load forever (need cookie to remember choice)
- Terrible UX for a logged-in app

**Legal:** Not required by GDPR/CCPA. Essential cookies are exempt from consent.

### Option 2: Accept All vs Essential Only ✅ (CURRENT)
**Why this works:**
- Essential cookies don't require consent (GDPR Article 6(1)(f))
- Analytics cookies are opt-in only
- Users can use the site fully with "Essential Only"
- Complies with all major privacy laws

**Legal Basis:**
- **Essential cookies:** Legitimate interest (GDPR Art. 6(1)(f))
- **Analytics cookies:** Explicit consent (GDPR Art. 6(1)(a))

### Option 3: Reject All (No Cookies at All) ⚠️
**Would require:**
- Server-side sessions instead of client-side JWT
- URL query parameters for consent state
- Complex architecture changes
- Still poor UX (can't stay logged in)

**Verdict:** Not worth the complexity for minimal legal benefit.

---

## GDPR/CCPA Compliance

### ✅ We're Compliant Because:

1. **Clear categorization** - Essential vs Analytics clearly labeled
2. **Granular control** - Users can accept only essential
3. **No pre-ticked boxes** - Analytics off by default
4. **Easy to find** - Banner visible on first visit
5. **Persistent choice** - No need to re-consent on every visit
6. **No dark patterns** - Both buttons equally prominent
7. **Privacy policy linked** - "Learn more" link provided

### 📋 Privacy Laws Coverage

| Law | Requirement | Our Implementation |
|-----|-------------|-------------------|
| **GDPR (EU)** | Consent for non-essential cookies | ✅ Analytics require consent |
| **CCPA (California)** | Opt-out of sale of personal info | ✅ No data sold, analytics opt-in |
| **PECR (UK)** | Similar to GDPR | ✅ Same as GDPR compliance |
| **ePrivacy Directive** | Cookie consent | ✅ Explicit consent for analytics |

---

## User Flow

```
┌─────────────────────────────────────────┐
│ User visits boardof.one                 │
│ (first time)                            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Cookie Banner Appears                   │
│                                         │
│ [Essential Only] [Accept All]          │
└────────┬────────────────┬───────────────┘
         │                │
         │                │
    Essential            Accept All
      Only
         │                │
         ▼                ▼
┌────────────────┐  ┌────────────────────┐
│ Stores:        │  │ Stores:            │
│ - Consent      │  │ - Consent          │
│ - Auth tokens  │  │ - Auth tokens      │
│                │  │ - Analytics OK     │
└────────────────┘  └────────────────────┘
         │                │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │ Banner Hidden  │
         │ Choice Saved   │
         └────────────────┘
```

---

## Implementation Details

### Cookie Attributes

```javascript
Cookies.set('bo1_cookie_consent', value, {
  expires: 365,        // 1 year
  sameSite: 'Lax',     // CSRF protection
  secure: true         // HTTPS only
});
```

### Consent Storage Format

```json
{
  "essential": true,
  "analytics": false,
  "timestamp": "2025-11-18T16:00:00.000Z"
}
```

### Theme Preference (Not a Cookie!)

Theme is stored in `localStorage`, not cookies:
```javascript
localStorage.setItem('theme', 'dark');
```

**Why?** Doesn't need to be sent to server, saves bandwidth.

---

## Future: Analytics Integration

When we add analytics (Week 10+), we'll use privacy-friendly options:

### Recommended: Plausible Analytics
- ✅ GDPR compliant by default
- ✅ No personal data collected
- ✅ Lightweight (<1KB script)
- ✅ EU-hosted option available
- ✅ No cookies needed (but we'll still ask for consent)

### Alternative: Fathom Analytics
- ✅ Similar to Plausible
- ✅ GDPR/CCPA compliant
- ✅ No cookies

### ❌ NOT Using: Google Analytics
- ❌ GDPR concerns (US data transfer)
- ❌ Heavy script (>100KB)
- ❌ Tracks users across sites
- ❌ Complex consent management

---

## Privacy Policy Requirements

You'll need a privacy policy page at `/privacy` that explains:

1. **What cookies we use** (list from table above)
2. **Why we use them** (auth, consent, analytics)
3. **How to manage cookies** (browser settings)
4. **Third parties** (Supabase, analytics provider)
5. **Data retention** (how long cookies last)
6. **User rights** (access, deletion, portability)
7. **Contact info** (privacy@boardof.one)

**Template:** Use [Termly](https://termly.io/) or [iubenda](https://www.iubenda.com/) to generate a compliant privacy policy.

---

## FAQ

### Q: Do we need a "Decline" button?
**A:** No. "Essential Only" is effectively a decline for optional cookies. Essential cookies are exempt from consent requirements.

### Q: What if user blocks all cookies in browser?
**A:** They won't be able to log in or stay logged in. This is acceptable - it's their choice.

### Q: Do we need a cookie management page?
**A:** Nice to have, not legally required. Users can clear cookies via browser settings.

### Q: How often must users re-consent?
**A:** Never, unless:
- They clear cookies
- We add new cookie categories
- 1 year passes (our cookie expires)

### Q: Can we use Google Analytics?
**A:** Technically yes with consent, but Plausible/Fathom are better for privacy and compliance.

---

## Testing Checklist

- [ ] Banner shows on first visit
- [ ] "Essential Only" sets `analytics: false`
- [ ] "Accept All" sets `analytics: true`
- [ ] Banner doesn't show on second visit
- [ ] Clearing cookies shows banner again
- [ ] Theme preference persists (localStorage)
- [ ] Auth works with "Essential Only"
- [ ] Analytics blocked with "Essential Only"
- [ ] Cookie has `secure: true` and `sameSite: Lax`
- [ ] Privacy policy link works

---

## Recommendation

**Keep the current implementation.** It's:
- ✅ GDPR/CCPA compliant
- ✅ User-friendly
- ✅ Industry best practice
- ✅ No need for "Decline All" button

**Minor improvements made:**
- ✅ Better copy explaining what essential cookies do
- ✅ Link to privacy policy
- ✅ More secure cookie attributes (`sameSite`, `secure`)
- ✅ Better visual hierarchy (ghost button for essential-only)
