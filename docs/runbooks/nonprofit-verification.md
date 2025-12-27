# Nonprofit/Charity Verification Runbook

This document describes the process for verifying nonprofit status and applying discounts.

## Overview

Bo1 offers discounted pricing for verified nonprofits and charities:
- **NONPROFIT80**: 80% discount for established nonprofits
- **NONPROFIT100**: 100% discount (free) for qualifying small charities

## Verification Process

### 1. Receive Request

Nonprofits can request discount status by:
- Emailing support with organization details
- Contacting via the help page

### 2. Required Documentation

Request the following from the applicant:

**UK Organizations:**
- Charity Commission registration number (look up at [gov.uk/find-charity-information](https://www.gov.uk/find-charity-information))
- Companies House registration (if applicable)

**US Organizations:**
- IRS 501(c)(3) determination letter
- EIN (Employer Identification Number)

**International:**
- Official charity registration certificate
- Government-issued nonprofit status documentation

### 3. Verification Steps

1. **Look up registration**: Verify the charity number matches official records
2. **Check active status**: Ensure registration is current, not expired or revoked
3. **Match organization name**: Confirm the registered name matches the application
4. **Review mission**: Ensure it's a genuine charitable mission (not a political PAC, trade association, etc.)

### 4. Apply Nonprofit Status

Once verified, apply status via Admin UI:

```bash
# Via API (if needed)
curl -X POST https://app.boardof.one/api/admin/users/{user_id}/nonprofit \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "org_name": "Doctors Without Borders",
    "apply_promo_code": "NONPROFIT80"
  }'
```

Or via Admin Dashboard:
1. Go to Admin > Users
2. Search for the user's email
3. Look for nonprofit badge in Badges column
4. Click "Promo" button and apply NONPROFIT80 or NONPROFIT100

### 5. Discount Tier Selection

| Tier | Discount | Criteria |
|------|----------|----------|
| NONPROFIT80 | 80% off | Established nonprofits with regular revenue |
| NONPROFIT100 | Free | Small charities, volunteer-run orgs, hardship cases |

**Guidelines for NONPROFIT100:**
- Organization is volunteer-run with no paid staff
- Annual budget under £50,000
- Primarily serves vulnerable populations
- Requested due to financial hardship

## Creating Promo Codes (One-time Setup)

Run this script in production to create the codes:

```bash
ssh root@139.59.201.65
cd /opt/bo1
docker-compose exec bo1 uv run python -m backend.scripts.create_nonprofit_promos
```

## Revoking Nonprofit Status

If a nonprofit loses their status or we discover fraud:

```bash
curl -X DELETE https://app.boardof.one/api/admin/users/{user_id}/nonprofit \
  -H "Authorization: Bearer {admin_token}"
```

Note: This removes the nonprofit badge but does NOT revoke already-applied promo codes. To revoke promos, use the Promotions admin panel.

## Audit Trail

All nonprofit status changes are logged in the audit_log table with:
- `action`: `nonprofit_status_set` or `nonprofit_status_removed`
- `details`: Organization name and promo code applied
- Admin user ID and timestamp

## FAQ

**Q: Can we verify automatically?**
A: Not currently. Manual verification ensures we catch edge cases (political orgs, trade associations, etc.).

**Q: What if someone disputes their rejection?**
A: Ask for additional documentation. Err on the side of generosity for small orgs.

**Q: How do we handle abuse?**
A: Revoke nonprofit status and promo, lock account if needed. Document in audit log.
