#!/usr/bin/env python
"""Script to create Stripe products and prices for meeting bundles.

Run with:
    docker-compose exec bo1 uv run python -m backend.scripts.create_meeting_tier_prices

Requirements:
    - STRIPE_SECRET_KEY environment variable must be set
    - Use test mode key for development

This creates 4 one-time products:
    - Bo1 1 Meeting: £10
    - Bo1 3 Meetings: £30
    - Bo1 5 Meetings: £50
    - Bo1 9 Meetings: £90
"""

import os
import sys


def main() -> None:
    """Create Stripe products and prices for meeting bundles."""
    import stripe

    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not api_key:
        print("ERROR: STRIPE_SECRET_KEY not set")
        sys.exit(1)

    stripe.api_key = api_key

    bundles = [
        {"meetings": 1, "price_gbp": 10},
        {"meetings": 3, "price_gbp": 30},
        {"meetings": 5, "price_gbp": 50},
        {"meetings": 9, "price_gbp": 90},
    ]

    print("Creating meeting bundle products and prices...")
    print("-" * 50)

    created_prices = []

    for bundle in bundles:
        meetings = bundle["meetings"]
        price_gbp = bundle["price_gbp"]
        product_name = f"Bo1 {meetings} Meeting{'s' if meetings > 1 else ''}"

        # Create product
        product = stripe.Product.create(
            name=product_name,
            description=f"Bundle of {meetings} Bo1 meeting{'s' if meetings > 1 else ''} "
            f"for AI-powered strategic deliberation.",
            metadata={
                "type": "meeting_bundle",
                "meetings": str(meetings),
            },
        )
        print(f"Created product: {product.id} - {product_name}")

        # Create price (one-time, GBP)
        price = stripe.Price.create(
            product=product.id,
            unit_amount=price_gbp * 100,  # Convert to pence
            currency="gbp",
            metadata={
                "type": "meeting_bundle",
                "meetings": str(meetings),
            },
        )
        print(f"  Created price: {price.id} - £{price_gbp}")

        created_prices.append(
            {
                "meetings": meetings,
                "product_id": product.id,
                "price_id": price.id,
                "amount": f"£{price_gbp}",
            }
        )

    print("-" * 50)
    print("\nAdd these to your environment variables:")
    print()
    for p in created_prices:
        env_var = f"STRIPE_PRICE_BUNDLE_{p['meetings']}"
        print(f"{env_var}={p['price_id']}")

    print("\nUpdate docs/runbooks/stripe-config.md with these price IDs.")


if __name__ == "__main__":
    main()
