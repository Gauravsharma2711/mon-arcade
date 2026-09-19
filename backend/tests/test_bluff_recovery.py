"""
Recovery and Failure Handling Tests for Bluff or Bust.

Verifies:
1. Refresh after joining (server returns complete match state, both players present, secret preserved).
2. Refresh during active match (decision phase, correct remaining time, can_act flag, secret preserved).
3. Invalid action (action when not your turn, invalid action string, action outside decision).
4. Duplicate action (concurrent or sequential duplicate decisions rejected).
5. Failed API request / match not found (404 Not Found with descriptive detail).
6. Already-resolved match (cannot submit action; state returns complete result).
7. Invalid reveal (commitment hash mismatch rejected with CommitmentVerificationError).
8. Timer/state expiration (authoritative timeout forfeit when turn deadline expires).
9. Opponent disconnect & re-entry (opponent state intact, re-entry restores full context).
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.game.bluff_engine import reset_bluff_engine, get_bluff_engine
from backend.app.game.bluff_models import BluffMatchStatus, BluffResolutionReason, BluffAction
from backend.app.game.bluff_crypto import create_commitment


@pytest.fixture
def client():
    reset_bluff_engine()
    with TestClient(app) as test_client:
        yield test_client
    reset_bluff_engine()


class TestBluffRecoveryAndFailures:
    """Test suite for failure resilience, refresh reconstruction, and error handling."""

    def test_refresh_after_joining(self, client: TestClient):
        """
        1. Refresh after joining:
        Alice creates match with secret 7.
        Bob joins with secret 3.
        Both simulate browser refresh by calling GET /api/bluff/match/{id}?player_id={id}.
        Server returns authoritative state without relying on lost React state.
        """
        # Alice creates match
        create_res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 7, "stake_amount": "5.0"},
        )
        assert create_res.status_code == 201
        match_id = create_res.json()["id"]

        # Bob joins
        join_res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob", "secret_value": 3},
        )
        assert join_res.status_code == 200

        # Simulate Alice page refresh
        alice_refresh = client.get(f"/api/bluff/match/{match_id}?player_id=0xalice")
        assert alice_refresh.status_code == 200
        alice_data = alice_refresh.json()
        assert alice_data["id"] == match_id
        assert alice_data["status"] == "DECISION"
        assert alice_data["creator"]["player_id"] == "0xalice"
        assert alice_data["creator"]["secret_value"] == 7  # Alice's secret preserved
        assert alice_data["opponent"]["player_id"] == "0xbob"
        assert alice_data["opponent"]["secret_value"] is None  # Bob's secret masked
        assert alice_data["is_creator"] is True
        assert alice_data["can_act"] is False  # Challenger Bob has the first turn

        # Simulate Bob page refresh
        bob_refresh = client.get(f"/api/bluff/match/{match_id}?player_id=0xbob")
        assert bob_refresh.status_code == 200
        bob_data = bob_refresh.json()
        assert bob_data["id"] == match_id
        assert bob_data["status"] == "DECISION"
        assert bob_data["opponent"]["player_id"] == "0xbob"
        assert bob_data["opponent"]["secret_value"] == 3  # Bob's secret preserved
        assert bob_data["creator"]["secret_value"] is None  # Alice's secret masked
        assert bob_data["is_creator"] is False
        assert bob_data["can_act"] is True  # Bob holds active turn

    def test_refresh_during_active_match(self, client: TestClient):
        """
        2. Refresh during active match:
        Verify turn clock, active player, and permissions are preserved on reload.
        """
        engine = get_bluff_engine()
        match = engine.create_match(creator_id="0xalice", secret_value=6, turn_seconds=20)
        engine.join_match(match_id=match.id, opponent_id="0xbob", secret_value=9)

        # Bob refreshes during active turn
        res = client.get(f"/api/bluff/match/{match.id}?player_id=0xbob")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DECISION"
        assert data["active_turn_player_id"] == "0xbob"
        assert data["can_act"] is True
        assert 0 < data["seconds_remaining"] <= 20
        assert data["pot_amount"] == "10.0"

    def test_invalid_action_handling(self, client: TestClient):
        """
        3. Invalid actions:
        - Non-active player acting out of turn (403)
        - Invalid action payload (422)
        - Action outside of DECISION state (400)
        """
        create_res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 7},
        )
        match_id = create_res.json()["id"]

        # Action on WAITING match -> 400
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xalice", "action": "PUSH"},
        )
        assert res.status_code == 400
        assert "DECISION" in res.json()["detail"]

        # Bob joins -> enters DECISION with Bob as active turn
        client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob", "secret_value": 5},
        )

        # Alice attempts action out of turn -> 403
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xalice", "action": "PUSH"},
        )
        assert res.status_code == 403
        assert "not player 0xalice's turn" in res.json()["detail"]

        # Invalid action string -> 422
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "INVALID_MOVE"},
        )
        assert res.status_code == 422

    def test_duplicate_action_handling(self, client: TestClient):
        """
        4. Duplicate action:
        Submitting action a second time is rejected and does not corrupt match resolution.
        """
        create_res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 8},
        )
        match_id = create_res.json()["id"]
        client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob", "secret_value": 4},
        )

        # First action succeeds
        first_res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "PUSH"},
        )
        assert first_res.status_code == 200
        assert first_res.json()["status"] == "RESOLVED"

        # Duplicate action attempt -> 410 Gone (match already resolved)
        dup_res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "PUSH"},
        )
        assert dup_res.status_code == 410
        assert "already RESOLVED" in dup_res.json()["detail"]

    def test_failed_api_request_and_not_found(self, client: TestClient):
        """
        5. Failed API request:
        Non-existent match returns 404 with explicit human-readable detail.
        """
        res = client.get("/api/bluff/match/bluff_nonexistent_999")
        assert res.status_code == 404
        assert "bluff_nonexistent_999" in res.json()["detail"]
        assert "not found" in res.json()["detail"].lower()

    def test_already_resolved_match_retrieval(self, client: TestClient):
        """
        6. Already-resolved match:
        Retrieval returns complete result structure, verified commitments, and resolution reason.
        """
        create_res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 8},
        )
        match_id = create_res.json()["id"]
        client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob", "secret_value": 4},
        )
        client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "PUSH"},
        )

        # Retrieve result via GET /api/bluff/match/{id}/result
        res = client.get(f"/api/bluff/match/{match_id}/result")
        assert res.status_code == 200
        result = res.json()
        assert result["winner_id"] == "0xalice"
        assert result["loser_id"] == "0xbob"
        assert result["is_tie"] is False
        assert result["creator_revealed"]["secret_value"] == 8
        assert result["opponent_revealed"]["secret_value"] == 4
        assert result["creator_revealed"]["commitment_verified"] is True
        assert result["opponent_revealed"]["commitment_verified"] is True

    def test_invalid_reveal_verification(self):
        """
        7. Invalid reveal:
        If commitment hash does not match revealed secret and salt, verification fails.
        """
        engine = get_bluff_engine()
        match = engine.create_match(creator_id="0xalice", secret_value=7)
        engine.join_match(match_id=match.id, opponent_id="0xbob", secret_value=3)

        # Tamper with creator's stored commitment hash to simulate corrupt/fraudulent reveal
        match.creator_commitment.commitment_hash = "0xdeadbeefbadhash"

        # Submitting action triggers reveal & verification -> raises CommitmentVerificationError
        with pytest.raises(Exception) as exc_info:
            engine.submit_action(match.id, "0xbob", BluffAction.PUSH)
        assert "commitment verification failed" in str(exc_info.value).lower()

    def test_timer_state_expiration_authoritative_resolution(self, client: TestClient):
        """
        8. Timer/state expiration:
        When a turn deadline expires, the server authoritatively resolves the match as timeout forfeit.
        """
        engine = get_bluff_engine()
        match = engine.create_match(creator_id="0xalice", secret_value=6, turn_seconds=5)
        engine.join_match(match_id=match.id, opponent_id="0xbob", secret_value=4)

        # Manually expire turn deadline into the past
        match.turn_deadline = datetime.now(timezone.utc) - timedelta(seconds=10)
        engine.store.save(match)

        # Client requests match view -> auto-triggers timeout resolution
        res = client.get(f"/api/bluff/match/{match.id}?player_id=0xalice")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution_reason"] == BluffResolutionReason.OPPONENT_TIMEOUT.value
        assert data["winner_id"] == "0xalice"
        assert data["can_act"] is False

    def test_opponent_disconnect_and_reentry(self, client: TestClient):
        """
        9. Opponent disconnect & re-entry:
        Opponent disconnects and rejoins with same player_id; state is seamlessly restored.
        """
        create_res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 9},
        )
        match_id = create_res.json()["id"]

        # Opponent joins
        client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob", "secret_value": 6},
        )

        # Opponent disconnects and re-enters
        reentry_res = client.get(f"/api/bluff/match/{match_id}?player_id=0xbob")
        assert reentry_res.status_code == 200
        data = reentry_res.json()
        assert data["id"] == match_id
        assert data["status"] == "DECISION"
        assert data["opponent"]["player_id"] == "0xbob"
        assert data["opponent"]["secret_value"] == 6
        assert data["creator"]["secret_value"] is None  # Host card remains secret
        assert data["can_act"] is True
