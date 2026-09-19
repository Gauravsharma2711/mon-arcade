import os
import re
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_db_status, init_db_pool, close_db_pool, get_db_pool
from backend.app.db.migrate import REQUIRED_TABLES
from backend.app.models.db_models import (
    UserModel,
    GameSessionModel,
    BluffMatchModel,
    VaultMatchModel,
    VaultTurnModel,
    SponsorModel,
    CampaignModel,
    PlacementModel,
    TransactionModel,
    ImpressionModel,
    ClickModel,
)

MIGRATION_FILE = Path(__file__).resolve().parent.parent.parent / "migrations" / "001_initial_schema.sql"


class TestDatabaseSchema:
    def test_migration_file_exists(self):
        """Ensure 001_initial_schema.sql exists and is non-empty."""
        assert MIGRATION_FILE.exists(), "migrations/001_initial_schema.sql must exist"
        content = MIGRATION_FILE.read_text(encoding="utf-8")
        assert len(content) > 100

    def test_all_eleven_tables_defined(self):
        """Ensure all 11 required tables and no unrelated tables are in the migration."""
        content = MIGRATION_FILE.read_text(encoding="utf-8")
        table_matches = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", content, re.IGNORECASE)
        table_names = [t.lower() for t in table_matches]

        for expected in REQUIRED_TABLES:
            assert expected in table_names, f"Expected table '{expected}' not found in migration"

        assert len(table_names) == 11, f"Expected exactly 11 tables, found {len(table_names)}: {table_names}"

    def test_server_owned_game_state_columns(self):
        """Validate that server owns authoritative game state and secrets."""
        content = MIGRATION_FILE.read_text(encoding="utf-8")

        # Bluff match secrets and resolution authority
        assert "creator_secret" in content, "bluff_matches must store creator_secret server-side"
        assert "opponent_secret" in content, "bluff_matches must store opponent_secret server-side"
        assert "winner_id" in content, "bluff_matches must store server-resolved winner_id"

        # Vault match status and turns authority
        assert "pot_amount" in content, "vault_matches must store pot_amount"
        assert "turns_allowed" in content, "vault_matches must track turns_allowed"
        assert "breach_triggered" in content, "vault_turns must record authoritative breach verdict"

    def test_sqlite_ddl_execution(self):
        """
        Execute the schema statements in an in-memory SQL database
        to verify that all table DDLs, foreign keys, and indexes parse cleanly.
        """
        content = MIGRATION_FILE.read_text(encoding="utf-8")
        # Adapt PostgreSQL-specific types for standard SQLite parsing
        sqlite_ddl = content
        sqlite_ddl = re.sub(r"TIMESTAMP WITH TIME ZONE", "TIMESTAMP", sqlite_ddl, flags=re.IGNORECASE)
        sqlite_ddl = re.sub(r"NUMERIC\(\d+,\s*\d+\)", "NUMERIC", sqlite_ddl, flags=re.IGNORECASE)
        sqlite_ddl = re.sub(r"BOOLEAN DEFAULT \w+", "INTEGER DEFAULT 0", sqlite_ddl, flags=re.IGNORECASE)
        sqlite_ddl = re.sub(r"BOOLEAN", "INTEGER", sqlite_ddl, flags=re.IGNORECASE)

        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.executescript(sqlite_ddl)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        created_tables = [row[0] for row in cursor.fetchall()]

        for expected in REQUIRED_TABLES:
            assert expected in created_tables, f"Table {expected} was not created"

        conn.close()

    def test_pydantic_models_instantiation(self):
        """Verify that all 11 database Pydantic models can be instantiated."""
        user = UserModel(id="u1", wallet_address="0x1234567890123456789012345678901234567890")
        assert user.wallet_address.startswith("0x")

        session = GameSessionModel(id="s1", game_type="bluff", user_id="u1")
        assert session.game_type == "bluff"

        bluff = BluffMatchModel(
            id="bm1",
            creator_id="u1",
            stake_amount=10.5,
            creator_secret=42,
            status="WAITING",
        )
        assert bluff.creator_secret == 42

        vault = VaultMatchModel(
            id="vm1",
            challenger_id="u1",
            warden_model="mock-warden",
            pot_amount=100.0,
            turns_allowed=3,
        )
        assert vault.turns_allowed == 3

        turn = VaultTurnModel(
            id="vt1",
            match_id="vm1",
            turn_number=1,
            attacker_prompt="open vault",
            warden_response="access denied",
            breach_triggered=False,
        )
        assert not turn.breach_triggered

        sponsor = SponsorModel(id="sp1", name="Monad Labs", tagline="Scale", url="https://monad.xyz")
        assert sponsor.name == "Monad Labs"

        campaign = CampaignModel(id="c1", sponsor_id="sp1", name="Launch", budget=500.0)
        assert campaign.budget == 500.0

        placement = PlacementModel(id="p1", campaign_id="c1", slot_type="marquee", active=True)
        assert placement.slot_type == "marquee"

        tx = TransactionModel(
            id="tx1",
            user_id="u1",
            tx_hash="0xabcd",
            tx_type="ENTRY_FEE",
            amount=5.0,
            status="CONFIRMED",
        )
        assert tx.status == "CONFIRMED"

        imp = ImpressionModel(id="imp1", placement_id="p1")
        assert imp.placement_id == "p1"

        clk = ClickModel(id="clk1", placement_id="p1")
        assert clk.placement_id == "p1"


class TestDatabaseConnectionAndHealth:
    def test_db_pool_lifecycle_and_status(self):
        """Ensure connection pool lifecycle behaves gracefully without crashing."""
        import asyncio

        async def _test():
            await close_db_pool()
            assert get_db_status() in ("disconnected", "closed")
            pool = await init_db_pool()
            status = get_db_status()
            assert status is not None
            await close_db_pool()

        asyncio.run(_test())

    def test_health_endpoint(self):
        """Ensure GET /api/health returns {'status': 'ok'}."""
        with TestClient(app) as client:
            res = client.get("/api/health")
            assert res.status_code == 200
            assert res.json() == {"status": "ok"}

    def test_detailed_health_endpoint(self):
        """Ensure GET /api/health/detailed reports system and adapter status."""
        with TestClient(app) as client:
            res = client.get("/api/health/detailed")
            assert res.status_code == 200
            body = res.json()
            assert body["status"] == "ok"
            assert "database" in body
            assert "adapters" in body
