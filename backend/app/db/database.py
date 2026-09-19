import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import asyncpg
from backend.app.config import settings

logger = logging.getLogger(__name__)

db_pool: Optional[asyncpg.Pool] = None
db_status: str = "disconnected"


async def init_db_pool() -> Optional[asyncpg.Pool]:
    """Initialize asyncpg connection pool from environment settings."""
    global db_pool, db_status
    if not settings.DATABASE_URL:
        db_status = "unconfigured"
        logger.info("DATABASE_URL not configured; running without database connection.")
        return None

    try:
        db_pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=10,
            timeout=5.0,
            command_timeout=10.0,
        )
        db_status = "connected"
        logger.info("PostgreSQL connection pool initialized successfully.")
        return db_pool
    except Exception as e:
        db_status = f"unavailable: {str(e)}"
        logger.warning(
            f"PostgreSQL connection failed ({e}). "
            "Backend will continue in standalone mode until database credentials are confirmed."
        )
        return None


async def close_db_pool():
    """Close asyncpg connection pool on application shutdown."""
    global db_pool, db_status
    if db_pool:
        await db_pool.close()
        db_pool = None
    db_status = "closed"
    logger.info("PostgreSQL connection pool closed.")


def get_db_pool() -> Optional[asyncpg.Pool]:
    """Return the active connection pool if initialized."""
    return db_pool


def get_db_status() -> str:
    """Return the current database connection status string."""
    return db_status


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Async context manager yielding a database connection from the pool."""
    if db_pool is None:
        raise RuntimeError(
            f"Database connection pool is not available. Status: {db_status}"
        )
    async with db_pool.acquire() as connection:
        yield connection
