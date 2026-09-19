"""
Mon Arcade Database Migration Runner (asyncpg / PostgreSQL)
Applies SQL migrations without requiring an ORM.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncpg

from backend.app.config import settings

logger = logging.getLogger("mon_arcade.migrate")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REQUIRED_TABLES = [
    "users",
    "game_sessions",
    "bluff_matches",
    "vault_matches",
    "vault_turns",
    "sponsors",
    "campaigns",
    "placements",
    "transactions",
    "impressions",
    "clicks",
]

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "migrations"


async def get_connection(dsn: Optional[str] = None) -> asyncpg.Connection:
    """Acquire an asyncpg connection using configured or supplied DSN."""
    target_dsn = dsn or settings.DATABASE_URL
    if not target_dsn:
        raise ValueError("DATABASE_URL is not set.")
    return await asyncpg.connect(dsn=target_dsn, timeout=5.0)


async def apply_sql_file(conn: asyncpg.Connection, filepath: Path) -> None:
    """Execute raw SQL statements from a migration file."""
    logger.info(f"Reading migration file: {filepath.name}")
    sql = filepath.read_text(encoding="utf-8")
    async with conn.transaction():
        await conn.execute(sql)
    logger.info(f"Successfully applied: {filepath.name}")


async def inspect_tables(conn: asyncpg.Connection) -> List[str]:
    """Query information_schema to return public table names."""
    rows = await conn.fetch(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
    )
    return [r["table_name"] for r in rows]


async def verify_schema(conn: asyncpg.Connection) -> Dict[str, Any]:
    """Verify that all 11 required tables exist."""
    existing_tables = await inspect_tables(conn)
    missing_tables = [tbl for tbl in REQUIRED_TABLES if tbl not in existing_tables]

    result = {
        "verified": len(missing_tables) == 0,
        "existing_tables": existing_tables,
        "required_tables": REQUIRED_TABLES,
        "missing_tables": missing_tables,
    }
    return result


async def run_migrations(dsn: Optional[str] = None) -> bool:
    """Apply all .sql migrations in migrations directory and verify."""
    try:
        conn = await get_connection(dsn)
    except Exception as e:
        logger.error(f"Cannot connect to PostgreSQL: {e}")
        return False

    try:
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not sql_files:
            logger.warning(f"No .sql migration files found in {MIGRATIONS_DIR}")
            return False

        for sql_file in sql_files:
            await apply_sql_file(conn, sql_file)

        verification = await verify_schema(conn)
        if verification["verified"]:
            logger.info("All 11 required tables verified in database:")
            for tbl in REQUIRED_TABLES:
                logger.info(f"  ✓ {tbl}")
            return True
        else:
            logger.error(f"Missing tables: {verification['missing_tables']}")
            return False
    finally:
        await conn.close()


def validate_schema_files() -> bool:
    """Validate migration files for all 11 required tables and constraints without needing live DB."""
    import re
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        logger.error(f"No .sql migration files found in {MIGRATIONS_DIR}")
        return False

    all_content = "\n".join(f.read_text(encoding="utf-8") for f in sql_files)
    table_matches = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", all_content, re.IGNORECASE)
    table_names = [t.lower() for t in table_matches]

    logger.info(f"Checking migration files: {[f.name for f in sql_files]}")
    missing = [tbl for tbl in REQUIRED_TABLES if tbl not in table_names]
    if missing:
        logger.error(f"Missing required tables in migration files: {missing}")
        return False

    logger.info(f"All {len(REQUIRED_TABLES)} required tables are defined:")
    for tbl in REQUIRED_TABLES:
        logger.info(f"  ✓ {tbl}")
    return True


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "--apply"
    if action == "--apply":
        success = asyncio.run(run_migrations())
        sys.exit(0 if success else 1)
    elif action == "--inspect":
        async def _inspect():
            conn = await get_connection()
            try:
                tables = await inspect_tables(conn)
                print("Existing tables:", tables)
            finally:
                await conn.close()
        asyncio.run(_inspect())
    elif action in ("--validate", "--verify"):
        valid = validate_schema_files()
        sys.exit(0 if valid else 1)
    else:
        print(f"Unknown option: {action}. Use --apply, --inspect, or --validate.")
