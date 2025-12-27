# Stripe Configuration Runbook

## Overview

Bo1 uses Stripe for subscription billing with three tiers: Free, Starter ($29/mo), Pro ($99/mo).

## Environment Variables

### Backend (secrets)
```
STRIPE_SECRET_KEY=sk_test_xxx or sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

### Frontend (public)
```
PUBLIC_STRIPE_PRICE_STARTER=price_xxx
PUBLIC_STRIPE_PRICE_PRO=price_xxx
```

## Test Mode Price IDs

| Product | Price ID | Amount |
|---------|----------|--------|
| Bo1 Starter | `price_TODO` | $29.00/month |
| Bo1 Pro | `price_TODO` | $99.00/month |

## Live Mode Price IDs

| Product | Price ID | Amount |
|---------|----------|--------|
| Bo1 Starter | `price_TODO` | $29.00/month |
| Bo1 Pro | `price_TODO` | $99.00/month |

> **Note:** Test and live mode use different price IDs. Update after going live.

## Setup Steps

### 1. Create Products (Stripe Dashboard)
1. Log into [Stripe Dashboard](https://dashboard.stripe.com)
2. Toggle to Test mode (top-right)
3. Products → Add product
4. Create "Bo1 Starter" with recurring price $29.00/month
5. Create "Bo1 Pro" with recurring price $99.00/month
6. Copy price IDs (format: `price_...`)

### 2. Configure Webhook
1. Developers → Webhooks → Add endpoint
2. URL: `https://api.boardof.one/api/v1/billing/webhook`
3. Events to send:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy signing secret → set as `STRIPE_WEBHOOK_SECRET`

### 3. Configure Customer Portal
1. Settings → Customer portal
2. Enable "Allow customers to switch plans"
3. Enable "Allow customers to cancel subscriptions"

### 4. Set Environment Variables
```bash
# .env.local (development)
PUBLIC_STRIPE_PRICE_STARTER=price_xxx
PUBLIC_STRIPE_PRICE_PRO=price_xxx

# Production (deployment secrets)
# Same variables with live mode price IDs
```

## Verification Checklist

- [ ] Products visible in Stripe Dashboard
- [ ] Checkout redirects to Stripe with correct amount
- [ ] Webhook `checkout.session.completed` updates user tier
- [ ] Billing portal shows subscription details
- [ ] Plan upgrade/downgrade works via portal

## Test Card

Use `4242 4242 4242 4242` with any future expiry and any CVC.

## Going Live

1. Toggle Stripe Dashboard to Live mode
2. Create identical products/prices
3. Update environment variables with live mode IDs
4. Update webhook endpoint URL if different
5. Update this runbook with live price IDs

---

_Last updated: 2025-12-27_
