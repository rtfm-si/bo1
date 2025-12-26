"""Seed initial T&C version (v1.0).

Revision ID: tc2_seed_initial_terms
Revises: tc1_add_terms_versioning
Create Date: 2025-12-26
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "tc2_seed_initial_terms"
down_revision: str | Sequence[str] | None = "tc1_add_terms_versioning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Initial T&C content (v1.0)
INITIAL_TERMS_CONTENT = """
# Terms and Conditions

**Effective Date: December 26, 2025**

## 1. Acceptance of Terms

By accessing and using Board of One ("the Service"), you agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use the Service.

## 2. Description of Service

Board of One is an AI-powered deliberation platform that helps users make strategic business decisions through multi-agent discussion and analysis.

## 3. User Accounts

- You must provide accurate and complete information when creating an account
- You are responsible for maintaining the security of your account credentials
- You must notify us immediately of any unauthorized access to your account

## 4. Acceptable Use

You agree not to:
- Use the Service for any unlawful purpose
- Attempt to gain unauthorized access to any part of the Service
- Interfere with or disrupt the Service or servers
- Upload malicious content or attempt to compromise system security

## 5. Intellectual Property

- The Service and its original content remain the property of Board of One
- User-generated content remains the property of the respective users
- You grant us a license to use your content to provide and improve the Service

## 6. Data Privacy

Your use of the Service is also governed by our Privacy Policy. By using the Service, you consent to the collection and use of your data as described therein.

## 7. AI-Generated Content

- The Service uses artificial intelligence to generate recommendations and analysis
- AI-generated content is for informational purposes only
- You should exercise independent judgment before acting on AI recommendations
- We do not guarantee the accuracy or suitability of AI-generated content

## 8. Limitation of Liability

The Service is provided "as is" without warranties of any kind. We shall not be liable for any indirect, incidental, special, consequential, or punitive damages.

## 9. Termination

We reserve the right to suspend or terminate your access to the Service at our discretion, with or without notice.

## 10. Changes to Terms

We may modify these terms at any time. Continued use of the Service after changes constitutes acceptance of the new terms.

## 11. Contact

For questions about these Terms and Conditions, please contact us at support@boardofone.com.
"""


def upgrade() -> None:
    """Seed initial T&C version."""
    op.execute(
        f"""
        INSERT INTO terms_versions (version, content, is_active, published_at)
        VALUES ('1.0', $terms${INITIAL_TERMS_CONTENT}$terms$, true, NOW())
        """
    )


def downgrade() -> None:
    """Remove initial T&C version."""
    op.execute("DELETE FROM terms_versions WHERE version = '1.0'")
