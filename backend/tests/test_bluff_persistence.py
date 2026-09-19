"""
Integration and Persistence Tests for Bluff or Bust Database Layer.

Verifies:
1. Migration 002 schema integrity and column definitions
2. Complete SQL persistence and exact domain model reconstruction
3. Process restart / cache-clearing reload survival across state progression
4. Authoritative match restoration endpoint GET /api/match/{id}
5. Strict separation between public match state, private player state, and revealed result state
"""

import sqlite3
from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.game.bluff_engine import BluffGameEngine, BluffMatchStore, reset_bluff_engine
from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffResolutionReason,
    BluffSettlementStatus,
)
from backend.app.db.bluff_repo import BluffRepository, get_bluff_repository

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


@pytest.fixture
def sqlite_db():
    """In-memory SQLite database connection with Mon Arcade schema applied."""
    conn = sqlite3.connect(":memory:")
    BluffRepository.init_sqlite_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def persistent_engine(sqlite_db):
    """Engine backed by persistent store simulating external database."""
    store = BluffMatchStore()
    store.set_sqlite_connection(sqlite_db)
    return BluffGameEngine(store=store)


class TestBluffDatabasePersistence:
    """Tests covering SQL migration, persistence, and state reconstruction."""

    def test_migration_002_file_and_columns(self):
        """Ensure 002_bluff_persistence.sql exists and defines all required persistence columns."""
        migration_file = MIGRATIONS_DIR / "002_bluff_persistence.sql"
        assert migration_file.exists(), "migrations/002_bluff_persistence.sql must exist"
        sql = migration_file.read_text(encoding="utf-8")

        required_columns = [
            "pot_amount",
            "creator_salt",
            "creator_commitment_hash",
            "creator_has_committed",
            "creator_action",
            "creator_action_at",
            "opponent_salt",
            "opponent_commitment_hash",
            "opponent_has_committed",
            "opponent_action",
            "opponent_action_at",
            "active_turn_player_id",
            "turn_deadline",
            "turn_seconds_allowed",
            "resolution_reason",
            "payout_tx_hash",
            "result_payload",
            "updated_at",
        ]

        for col in required_columns:
            assert col in sql, f"Column '{col}' must be defined in migration 002"

    def test_sql_persistence_and_exact_reconstruction(self, persistent_engine: BluffGameEngine, sqlite_db):
        """
        Verify that saving a match to SQL and restoring it recreates
        the identical authoritative domain model without data loss.
        """
        match = persistent_engine.create_match(
            creator_id="0xalice",
            stake_amount=Decimal("12.5"),
            secret_value=7,
            turn_seconds=20,
        )

        # Retrieve raw row from SQLite directly to verify column storage
        sqlite_db.row_factory = sqlite3.Row
        cursor = sqlite_db.cursor()
        cursor.execute("SELECT * FROM bluff_matches WHERE id = ?", (match.id,))
        row = dict(cursor.fetchone())

        assert row["id"] == match.id
        assert row["creator_id"] == "0xalice"
        assert float(row["stake_amount"]) == 12.5
        assert float(row["pot_amount"]) == 25.0
        assert row["creator_secret"] == 7
        assert row["creator_salt"] == match.creator_commitment.salt
        assert row["creator_commitment_hash"] == match.creator_commitment.commitment_hash
        assert row["creator_has_committed"] == 1
        assert row["status"] == "WAITING"

        # Reconstruct domain model from database row
        reconstructed = BluffRepository.row_to_match(row)
        assert reconstructed.id == match.id
        assert reconstructed.creator_id == "0xalice"
        assert reconstructed.stake_amount == Decimal("12.5")
        assert reconstructed.pot_amount == Decimal("25.0")
        assert reconstructed.creator_commitment.secret_value == 7
        assert reconstructed.creator_commitment.salt == match.creator_commitment.salt
        assert reconstructed.creator_commitment.commitment_hash == match.creator_commitment.commitment_hash
        assert reconstructed.creator_commitment.has_committed is True
        assert reconstructed.status == BluffMatchStatus.WAITING

    def test_process_reload_survival_across_state_progression(
        self, persistent_engine: BluffGameEngine
    ):
        """
        Simulates process reload (in-memory cache cleared) at each lifecycle step:
        1. Created -> cache cleared -> restored
        2. Joined -> cache cleared -> restored in DECISION
        3. PUSH decision -> cache cleared -> restored in RESOLVED with result
        """
        # Step 1: Create
        match = persistent_engine.create_match(
            creator_id="0xalice",
            stake_amount=Decimal("5.0"),
            secret_value=9,
        )
        match_id = match.id

        # Simulate process reboot / memory wipe
        persistent_engine.store.clear()
        assert match_id not in persistent_engine.store._matches

        # Restore from database
        restored = persistent_engine.get_match(match_id)
        assert restored is not None
        assert restored.id == match_id
        assert restored.status == BluffMatchStatus.WAITING
        assert restored.creator_commitment.secret_value == 9

        # Step 2: Opponent joins
        joined = persistent_engine.join_match(match_id, opponent_id="0xbob", secret_value=6)
        assert joined.status == BluffMatchStatus.DECISION

        # Simulate second process reboot
        persistent_engine.store.clear()
        assert match_id not in persistent_engine.store._matches

        # Restore from database
        restored_decision = persistent_engine.get_match(match_id)
        assert restored_decision is not None
        assert restored_decision.status == BluffMatchStatus.DECISION
        assert restored_decision.opponent_id == "0xbob"
        assert restored_decision.active_turn_player_id == "0xbob"
        assert restored_decision.opponent_commitment.secret_value == 6

        # Step 3: Action submitted (Showdown PUSH)
        resolved = persistent_engine.submit_action(match_id, player_id="0xbob", action=BluffAction.PUSH)
        assert resolved.status == BluffMatchStatus.RESOLVED
        assert resolved.winner_id == "0xalice"

        # Simulate third process reboot
        persistent_engine.store.clear()
        assert match_id not in persistent_engine.store._matches

        # Restore final showdown result
        restored_final = persistent_engine.get_match(match_id)
        assert restored_final is not None
        assert restored_final.status == BluffMatchStatus.RESOLVED
        assert restored_final.winner_id == "0xalice"
        assert restored_final.resolution_reason == BluffResolutionReason.SHOWDOWN_HIGHER_CARD
        assert restored_final.result is not None
        assert restored_final.result.winner_id == "0xalice"
        assert restored_final.result.loser_id == "0xbob"
        assert restored_final.result.creator_revealed.secret_value == 9
        assert restored_final.result.opponent_revealed.secret_value == 6
        assert restored_final.result.settlement_status == BluffSettlementStatus.SETTLED

    def test_restoration_endpoint_get_api_match_id(self):
        """Verify the authoritative restoration endpoint GET /api/match/{id}."""
        reset_bluff_engine()

        with TestClient(app) as client:
            # 1. Create match
            res = client.post(
                "/api/bluff/create",
                json={"creator_id": "0xcreator", "stake_amount": "5.0", "secret_value": 8},
            )
            assert res.status_code == 201
            match_id = res.json()["id"]

            # 2. Restore via GET /api/match/{id}
            res = client.get(f"/api/match/{match_id}?player_id=0xcreator")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == match_id
            assert data["is_creator"] is True
            assert data["creator"]["secret_value"] == 8
            assert data["opponent"] is None

            # 3. Join opponent
            client.post(
                f"/api/bluff/match/{match_id}/join",
                json={"player_id": "0xopponent", "secret_value": 3},
            )

            # 4. Restore for opponent: sees own secret (3), creator secret is hidden (null)
            res = client.get(f"/api/match/{match_id}?player_id=0xopponent")
            assert res.status_code == 200
            opp_data = res.json()
            assert opp_data["status"] == "DECISION"
            assert opp_data["opponent"]["secret_value"] == 3
            assert opp_data["creator"]["secret_value"] is None  # Never leaked!

            # 5. Restore for creator: sees own secret (8), opponent secret is hidden (null)
            res = client.get(f"/api/match/{match_id}?player_id=0xcreator")
            assert res.status_code == 200
            creator_data = res.json()
            assert creator_data["creator"]["secret_value"] == 8
            assert creator_data["opponent"]["secret_value"] is None  # Never leaked!

            # 6. Restore for spectator: neither secret is visible
            res = client.get(f"/api/match/{match_id}?player_id=0xspectator")
            assert res.status_code == 200
            spec_data = res.json()
            assert spec_data["creator"]["secret_value"] is None
            assert spec_data["opponent"]["secret_value"] is None

            # 7. Resolve match via PUSH
            client.post(
                f"/api/bluff/match/{match_id}/decision",
                json={"player_id": "0xopponent", "action": "PUSH"},
            )

            # 8. Restore after resolution: both secrets revealed to everyone
            res = client.get(f"/api/match/{match_id}?player_id=0xspectator")
            assert res.status_code == 200
            resolved_data = res.json()
            assert resolved_data["status"] == "RESOLVED"
            assert resolved_data["creator"]["secret_value"] == 8
            assert resolved_data["opponent"]["secret_value"] == 3
            assert resolved_data["winner_id"] == "0xcreator"
            assert resolved_data["result"] is not None

    def test_state_separation_guarantees(self, persistent_engine: BluffGameEngine):
        """
        Verify that database storage separates:
        1. Public match state (hashes, stakes, pot, timing)
        2. Private player state (secrets, salts)
        3. Revealed result state (audited showdown)
        """
        match = persistent_engine.create_match(
            creator_id="0xalice",
            stake_amount=Decimal("10.0"),
            secret_value=5,
        )
        persistent_engine.join_match(match.id, opponent_id="0xbob", secret_value=7)

        # In DECISION state:
        # Public view has commitment hashes for auditability
        alice_view = persistent_engine.get_client_view(match.id, viewer_id="0xalice")
        assert alice_view.creator.commitment_hash is not None
        assert alice_view.opponent.commitment_hash is not None

        # Private secrets: Alice cannot see Bob's secret; Bob cannot see Alice's
        assert alice_view.opponent.secret_value is None
        assert alice_view.opponent.salt is None

        bob_view = persistent_engine.get_client_view(match.id, viewer_id="0xbob")
        assert bob_view.creator.secret_value is None
        assert bob_view.creator.salt is None

        # Result is None before resolution
        assert alice_view.result is None
        assert bob_view.result is None
