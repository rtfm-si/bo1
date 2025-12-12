"""Encrypt existing OAuth tokens at rest.

Changes google_oauth_tokens column from JSONB to TEXT for encrypted storage.
Migrates existing plaintext tokens to encrypted format.

Revision ID: s1_encrypt_oauth_tokens
Revises: r1_add_user_retention_setting
Create Date: 2025-12-12
"""

import json
import logging
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "s1_encrypt_oauth_tokens"
down_revision: str | Sequence[str] | None = "r1_add_user_retention_setting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def get_encryption_key() -> str | None:
    """Get encryption key from environment."""
    return os.getenv("ENCRYPTION_KEY", "")


def encrypt_token_data(data: dict) -> str:
    """Encrypt token data using Fernet."""
    from cryptography.fernet import Fernet

    key = get_encryption_key()
    if not key:
        # No key = store as JSON (dev mode)
        return json.dumps(data)

    fernet = Fernet(key.encode())
    plaintext = json.dumps(data).encode()
    return fernet.encrypt(plaintext).decode()


def decrypt_token_data(ciphertext: str) -> dict | None:
    """Decrypt token data using Fernet."""
    from cryptography.fernet import Fernet, InvalidToken

    key = get_encryption_key()
    if not key:
        # No key = assume JSON
        try:
            return json.loads(ciphertext)
        except json.JSONDecodeError:
            return None

    try:
        fernet = Fernet(key.encode())
        plaintext = fernet.decrypt(ciphertext.encode())
        return json.loads(plaintext.decode())
    except (InvalidToken, json.JSONDecodeError):
        return None


def upgrade() -> None:
    """Encrypt existing OAuth tokens and change column type."""
    conn = op.get_bind()

    # Step 1: Add temporary TEXT column for encrypted data
    op.add_column(
        "users",
        sa.Column("google_oauth_tokens_encrypted", sa.Text, nullable=True),
    )

    # Step 2: Migrate existing tokens to encrypted format
    result = conn.execute(
        sa.text("SELECT id, google_oauth_tokens FROM users WHERE google_oauth_tokens IS NOT NULL")
    )
    rows = result.fetchall()

    encryption_key = get_encryption_key()
    migrated = 0
    skipped = 0

    for row in rows:
        user_id = row[0]
        tokens = row[1]

        if tokens is None:
            continue

        # Handle both dict (from JSONB) and string formats
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except json.JSONDecodeError:
                logger.warning(f"Skipping user {user_id}: invalid JSON in tokens")
                skipped += 1
                continue

        if not isinstance(tokens, dict):
            logger.warning(f"Skipping user {user_id}: unexpected token format")
            skipped += 1
            continue

        # Encrypt and store
        try:
            encrypted = encrypt_token_data(tokens)
            conn.execute(
                sa.text(
                    "UPDATE users SET google_oauth_tokens_encrypted = :encrypted WHERE id = :user_id"
                ),
                {"encrypted": encrypted, "user_id": user_id},
            )
            migrated += 1
        except Exception as e:
            logger.error(f"Failed to encrypt tokens for user {user_id}: {e}")
            skipped += 1

    logger.info(
        f"Token encryption migration: {migrated} migrated, {skipped} skipped"
        + (", using encryption" if encryption_key else ", storing as plaintext (no key)")
    )

    # Step 3: Drop old JSONB column
    op.drop_column("users", "google_oauth_tokens")

    # Step 4: Rename new column to original name
    op.alter_column(
        "users",
        "google_oauth_tokens_encrypted",
        new_column_name="google_oauth_tokens",
    )


def downgrade() -> None:
    """Decrypt tokens and restore JSONB column."""
    from sqlalchemy.dialects.postgresql import JSONB

    conn = op.get_bind()

    # Step 1: Add temporary JSONB column
    op.add_column(
        "users",
        sa.Column("google_oauth_tokens_decrypted", JSONB, nullable=True),
    )

    # Step 2: Decrypt and migrate back
    result = conn.execute(
        sa.text("SELECT id, google_oauth_tokens FROM users WHERE google_oauth_tokens IS NOT NULL")
    )
    rows = result.fetchall()

    for row in rows:
        user_id = row[0]
        encrypted = row[1]

        if encrypted is None:
            continue

        # Try to decrypt
        try:
            tokens = decrypt_token_data(encrypted)
            if tokens:
                conn.execute(
                    sa.text(
                        "UPDATE users SET google_oauth_tokens_decrypted = :tokens::jsonb WHERE id = :user_id"
                    ),
                    {"tokens": json.dumps(tokens), "user_id": user_id},
                )
        except Exception as e:
            logger.warning(f"Could not decrypt tokens for user {user_id}: {e}")

    # Step 3: Drop encrypted column
    op.drop_column("users", "google_oauth_tokens")

    # Step 4: Rename decrypted column
    op.alter_column(
        "users",
        "google_oauth_tokens_decrypted",
        new_column_name="google_oauth_tokens",
    )
