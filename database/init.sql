-- This script initializes the database for the AllergyMenuAssistant.
-- It stores only the necessary information: user identity, their allergies, and their API key.

-- Users Table
-- This table links a user from a specific platform (like Telegram or Line)
-- to a single, stable internal ID. This ID is then used to associate the user
-- with their allergies and API key. This avoids data duplication and keeps the schema clean.
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (platform, platform_user_id)
);

-- Allergies Table
-- A master list of all possible allergies.
CREATE TABLE allergies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- User Allergies Junction Table
-- Links a user's internal ID to their specific allergies.
CREATE TABLE user_allergies (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    allergy_id INTEGER NOT NULL REFERENCES allergies(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, allergy_id)
);

-- User API Keys Table
-- Securely stores an encrypted API key for a user.
CREATE TABLE user_api_keys (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    encrypted_api_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger to automatically update the 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_api_keys_updated_at
BEFORE UPDATE ON user_api_keys
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
