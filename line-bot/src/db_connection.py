import logging
import os

import asyncpg

# Get the database connection details from environment variables
DB_DATABASE = os.getenv("DB_DATABASE", "AllergyMenuAssistant")
DB_USERNAME = os.getenv("DB_USERNAME", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOSTNAME = os.getenv("DB_HOSTNAME", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to hold the pool
db_pool = None


async def init_db_pool(*args):
    global db_pool
    # Create a pool with min 1 connection and max 20 connections
    db_pool = await asyncpg.create_pool(
        dsn=f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_DATABASE}",
        min_size=1,
        max_size=20,
    )
    logging.info("Database pool created")


async def get_db_pool():
    if not db_pool:
        raise RuntimeError("Database pool not initialized")
    return db_pool


async def close_db_pool(*args):
    global db_pool
    if db_pool:
        await db_pool.close()
        logging.info("Database pool closed")
