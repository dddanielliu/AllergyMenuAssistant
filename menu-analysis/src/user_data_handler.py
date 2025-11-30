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


# --- Helper Functions ---

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


async def _get_user(platform: str, platform_user_id: str) -> int | None:
    """
    Retrieves the internal ID of a user from the database.
    If the user does not exist, it creates a new entry and returns the new ID.
    """
    platform_user_id = str(platform_user_id)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Use a transaction to make the get-or-create operation atomic
        async with conn.transaction():
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE platform = $1 AND platform_user_id = $2",
                platform,
                platform_user_id,
            )
            if user_id:
                return user_id
            else:
                return None

async def get_api_key(platform: str, platform_user_id: str | int) -> str | None:
    """Retrieves and decrypts the user's API key from the database."""
    platform_user_id = str(platform_user_id)
    internal_user_id = await _get_user(platform, platform_user_id)
    if not internal_user_id:
        return None

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        encrypted_key = await conn.fetchval(
            "SELECT encrypted_api_key FROM user_api_keys WHERE user_id = $1",
            internal_user_id,
        )
        if encrypted_key:
            return _decrypt_key(encrypted_key)
        return None
