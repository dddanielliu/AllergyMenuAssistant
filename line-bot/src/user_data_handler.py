import base64
import hashlib
import logging
import os
from typing import List

from cryptography.fernet import Fernet

from .db_connection import get_db_pool

# --- Encryption Setup ---

# Get the encryption key from environment variables.
# For Fernet, the key must be 32 bytes and URL-safe base64 encoded.
# We derive a suitable key from the user-provided string using SHA-256.
ENCRYPTION_KEY_STRING = os.getenv("USER_GEMINI_API_ENCRYPTION_KEY")
if not ENCRYPTION_KEY_STRING:
    raise ValueError("USER_GEMINI_API_ENCRYPTION_KEY environment variable not set.")

# Use SHA-256 to create a 32-byte key and then base64 encode it.
hashed_key = hashlib.sha256(ENCRYPTION_KEY_STRING.encode()).digest()
fernet_key = base64.urlsafe_b64encode(hashed_key)
_fernet = Fernet(fernet_key)





PLATFORM = "line"


# --- Helper Functions ---


def _encrypt_key(key: str) -> str:
    """Encrypts an API key using Fernet symmetric encryption."""
    return _fernet.encrypt(key.encode("utf-8")).decode("utf-8")


def _decrypt_key(encrypted_key: str) -> str | None:
    """
    Decrypts an API key using Fernet.
    Returns None if decryption fails (e.g., invalid key or corrupted data).
    """
    try:
        return _fernet.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logging.error(f"Failed to decrypt key: {e}")
        return None


async def _get_or_create_user(platform_user_id: str) -> int:
    """
    Retrieves the internal ID of a user from the database.
    If the user does not exist, it creates a new entry and returns the new ID.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Use a transaction to make the get-or-create operation atomic
        async with conn.transaction():
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE platform = $1 AND platform_user_id = $2",
                PLATFORM,
                platform_user_id,
            )
            if user_id:
                return user_id
            else:
                return await conn.fetchval(
                    "INSERT INTO users (platform, platform_user_id) VALUES ($1, $2) RETURNING id",
                    PLATFORM,
                    platform_user_id,
                )


# --- Public API ---


async def get_allergies(user_id: str | int) -> List[str]:
    """Get a user's allergies from the database."""
    user_id = str(user_id)
    internal_user_id = await _get_or_create_user(user_id)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT a.name
            FROM allergies a
            JOIN user_allergies ua ON a.id = ua.allergy_id
            WHERE ua.user_id = $1
            """,
            internal_user_id,
        )
        return [record["name"] for record in records]


async def update_allergies(user_id: str | int, allergies: List[str]) -> None:
    """Add, replace, or clear a user's allergies in the database."""
    user_id = str(user_id)
    internal_user_id = await _get_or_create_user(user_id)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Clear existing allergies for the user to ensure a clean replace
            await conn.execute(
                "DELETE FROM user_allergies WHERE user_id = $1", internal_user_id
            )

            if not allergies:
                return  # Just clear if the list is empty

            # Process new allergies
            for allergy_name in allergies:
                # Use INSERT ... ON CONFLICT to get or create the allergy_id in a single step.
                allergy_id = await conn.fetchval(
                    """
                    INSERT INTO allergies (name) VALUES ($1)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    allergy_name,
                )
                # Link allergy to user
                await conn.execute(
                    "INSERT INTO user_allergies (user_id, allergy_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    internal_user_id,
                    allergy_id,
                )


async def set_api_key(user_id: str | int, api_key: str | None) -> None:
    """Set or delete a user's API key in the database. The API key is encrypted before storing."""
    user_id = str(user_id)
    internal_user_id = await _get_or_create_user(user_id)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if api_key is None:
            # Delete the key
            await conn.execute(
                "DELETE FROM user_api_keys WHERE user_id = $1", internal_user_id
            )
        else:
            # Encrypt and upsert the key
            encrypted_key = _encrypt_key(api_key)
            await conn.execute(
                """
                INSERT INTO user_api_keys (user_id, encrypted_api_key)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET encrypted_api_key = EXCLUDED.encrypted_api_key, updated_at = NOW()
                """,
                internal_user_id,
                encrypted_key,
            )


async def get_api_key(user_id: str | int) -> str | None:
    """Retrieves and decrypts the user's API key from the database."""
    user_id = str(user_id)
    internal_user_id = await _get_or_create_user(user_id)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        encrypted_key = await conn.fetchval(
            "SELECT encrypted_api_key FROM user_api_keys WHERE user_id = $1",
            internal_user_id,
        )
        if encrypted_key:
            return _decrypt_key(encrypted_key)
        return None


async def delete_user(platform_user_id: str | int) -> None:
    """Deletes a user and cascades delete the user's keys and allergies.

    This deletes the database row from the `users` table matching the platform
    and the given platform user id. The DB schema includes `ON DELETE CASCADE`
    so related rows will be removed automatically.
    """
    platform_user_id = str(platform_user_id)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM users WHERE platform = $1 AND platform_user_id = $2",
            PLATFORM,
            platform_user_id,
        )
