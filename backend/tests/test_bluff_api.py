"""
FastAPI HTTP Endpoint Integration Tests for Bluff or Bust.

Tests all 7 required endpoints + lobbies/cancellation using FastAPI TestClient:
1. POST /api/bluff/create           - Create match
2. GET  /api/bluff/match/{id}       - Get match (sanitized client view)
3. POST /api/bluff/match/{id}/join  - Join match
4. POST /api/bluff/match/{id}/commit - Submit commitment
5. POST /api/bluff/match/{id}/decision - Submit Push/Fold decision
6. POST /api/bluff/match/{id}/reveal - Authoritative reveal & verification
7. GET  /api/bluff/match/{id}/result - Get resolved showdown result
8. GET  /api/bluff/lobbies          - List open lobbies
9. POST /api/bluff/match/{id}/cancel - Cancel open lobby

Verifies error conditions:
- Match not found (404)
- Unauthorized player (403)
- Invalid state transition (400)
- Conflict / already joined (409)
- Invalid action / secret value (422)
- Expired / closed match (410)
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.game.bluff_engine import reset_bluff_engine
from backend.app.game.bluff_models import BluffMatchStatus, BluffResolutionReason, BluffSettlementStatus


@pytest.fixture
def client():
    """Provides a TestClient with a fresh BluffGameEngine for each test."""
    reset_bluff_engine()
    with TestClient(app) as test_client:
        yield test_client
    reset_bluff_engine()


class TestBluffAPIEndpoints:
    """Comprehensive test suite for Bluff API routes."""

    def test_complete_duel_flow_via_http(self, client: TestClient):
        """
        Complete end-to-end API duel flow:
        1. Alice creates match (stake: 5 MON, secret: 8)
        2. Bob browses lobbies and sees Alice's match
        3. Bob joins match (secret: 4)
        4. Match enters DECISION
        5. Verify state masking (Alice cannot see Bob's 4, Bob cannot see Alice's 8)
        6. Bob submits PUSH action
        7. Reveal & result verification (8 > 4 -> Alice wins)
        8. Public result retrieval
        """
        # 1. Create Match
        res = client.post(
            "/api/bluff/create",
            json={
                "creator_id": "0xalice",
                "stake_amount": "5.0",
                "secret_value": 8,
                "turn_seconds": 15,
            },
        )
        assert res.status_code == 201
        data = res.json()
        match_id = data["id"]
        assert data["status"] == "WAITING"
        assert data["creator"]["player_id"] == "0xalice"
        assert data["creator"]["secret_value"] == 8
        assert data["creator"]["has_committed"] is True
        assert data["opponent"] is None

        # 2. List Lobbies
        res = client.get("/api/bluff/lobbies")
        assert res.status_code == 200
        lobbies = res.json()
        assert any(m["id"] == match_id for m in lobbies)

        # 3. Bob Joins Match
        res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={
                "player_id": "0xbob",
                "secret_value": 4,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "DECISION"
        assert data["opponent"]["player_id"] == "0xbob"
        assert data["active_turn_player_id"] == "0xbob"
        assert data["opponent"]["secret_value"] == 4  # Bob sees own secret
        assert data["creator"]["secret_value"] is None  # Bob cannot see Alice's secret!

        # 4. Check View Sanitization from Alice's Perspective
        res = client.get(f"/api/bluff/match/{match_id}?player_id=0xalice")
        assert res.status_code == 200
        alice_data = res.json()
        assert alice_data["creator"]["secret_value"] == 8
        assert alice_data["opponent"]["secret_value"] is None  # Alice cannot see Bob's secret!
        assert alice_data["can_act"] is False

        # Check View Sanitization from Spectator's Perspective
        res = client.get(f"/api/bluff/match/{match_id}?player_id=0xstranger")
        assert res.status_code == 200
        spectator_data = res.json()
        assert spectator_data["creator"]["secret_value"] is None
        assert spectator_data["opponent"]["secret_value"] is None
        assert spectator_data["can_act"] is False

        # 5. Bob Submits PUSH Action
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={
                "player_id": "0xbob",
                "action": "PUSH",
            },
        )
        assert res.status_code == 200
        resolved_data = res.json()
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["winner_id"] == "0xalice"
        assert resolved_data["resolution_reason"] == "SHOWDOWN_HIGHER_CARD"
        assert resolved_data["payout_tx_hash"] is not None

        # 6. Call Reveal Endpoint
        res = client.post(f"/api/bluff/match/{match_id}/reveal")
        assert res.status_code == 200
        reveal_data = res.json()
        assert reveal_data["match_id"] == match_id
        assert reveal_data["status"] == "RESOLVED"
        assert reveal_data["winner_id"] == "0xalice"
        assert reveal_data["creator_revealed"]["secret_value"] == 8
        assert reveal_data["creator_revealed"]["commitment_verified"] is True
        assert reveal_data["opponent_revealed"]["secret_value"] == 4
        assert reveal_data["opponent_revealed"]["commitment_verified"] is True

        # 7. Get Result Endpoint
        res = client.get(f"/api/bluff/match/{match_id}/result")
        assert res.status_code == 200
        result_data = res.json()
        assert result_data["match_id"] == match_id
        assert result_data["winner_id"] == "0xalice"
        assert result_data["loser_id"] == "0xbob"
        assert result_data["is_tie"] is False
        assert result_data["settlement_status"] == "SETTLED"

    def test_sequential_commitments_and_fold_victory(self, client: TestClient):
        """
        Tests:
        1. Match created without secret
        2. Opponent joins without secret
        3. Both submit commitments sequentially via POST /commit
        4. Bob folds via POST /decision
        5. Alice wins uncontested
        """
        # Create uncommitted
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "stake_amount": "10.0"},
        )
        assert res.status_code == 201
        match_id = res.json()["id"]
        assert res.json()["creator"]["has_committed"] is False

        # Join uncommitted
        res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xbob"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"

        # Alice commits secret 3
        res = client.post(
            f"/api/bluff/match/{match_id}/commit",
            json={"player_id": "0xalice", "secret_value": 3},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"
        assert res.json()["creator"]["has_committed"] is True

        # Bob commits secret 9 -> transitions to DECISION
        res = client.post(
            f"/api/bluff/match/{match_id}/commit",
            json={"player_id": "0xbob", "secret_value": 9},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "DECISION"
        assert res.json()["opponent"]["has_committed"] is True

        # Bob chooses FOLD (surrender)
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "FOLD"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RESOLVED"
        assert data["winner_id"] == "0xalice"
        assert data["resolution_reason"] == "OPPONENT_FOLDED"

    def test_validation_errors(self, client: TestClient):
        """Verify API validations and status codes."""
        # 1. Invalid secret value (< 1 or > 10)
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 11},
        )
        assert res.status_code == 422

        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 0},
        )
        assert res.status_code == 422

        # 2. Invalid stake amount (<= 0)
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "stake_amount": "0.0"},
        )
        assert res.status_code == 422

        # 3. Match not found (404)
        res = client.get("/api/bluff/match/bluff_non_existent")
        assert res.status_code == 404

        # Create valid match for subsequent checks
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 5},
        )
        match_id = res.json()["id"]

        # 4. Creator cannot duel themselves (403)
        res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xalice", "secret_value": 5},
        )
        assert res.status_code == 403

        # 5. Non-participant cannot commit (403)
        res = client.post(
            f"/api/bluff/match/{match_id}/commit",
            json={"player_id": "0xcharlie", "secret_value": 5},
        )
        assert res.status_code == 403

        # Join Bob
        client.post(f"/api/bluff/match/{match_id}/join", json={"player_id": "0xbob", "secret_value": 6})

        # 6. Third player cannot join full match (400)
        res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": "0xcharlie", "secret_value": 6},
        )
        assert res.status_code == 400

        # 7. Player committing twice (409 Conflict)
        res = client.post(
            f"/api/bluff/match/{match_id}/commit",
            json={"player_id": "0xalice", "secret_value": 7},
        )
        assert res.status_code in (400, 409)

        # 8. Inactive player acting out of turn (403)
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xalice", "action": "PUSH"},
        )
        assert res.status_code == 403

        # 9. Invalid action string (422)
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "INVALID_ACTION"},
        )
        assert res.status_code == 422

        # 10. Querying result before resolved (400)
        res = client.get(f"/api/bluff/match/{match_id}/result")
        assert res.status_code == 400

        # Resolve match
        client.post(f"/api/bluff/match/{match_id}/decision", json={"player_id": "0xbob", "action": "PUSH"})

        # 11. Acting on already-resolved match (410 Gone)
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xbob", "action": "PUSH"},
        )
        assert res.status_code == 410

    def test_lobby_cancellation(self, client: TestClient):
        """Creator can cancel match before opponent joins; non-creator cannot."""
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xalice", "secret_value": 5},
        )
        match_id = res.json()["id"]

        # Non-creator attempts cancel -> 403
        res = client.post(
            f"/api/bluff/match/{match_id}/cancel",
            json={"player_id": "0xbob"},
        )
        assert res.status_code == 403

        # Creator cancels -> 200 CANCELLED
        res = client.post(
            f"/api/bluff/match/{match_id}/cancel",
            json={"player_id": "0xalice"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "CANCELLED"

        # Cancelled match is no longer in open lobbies
        res = client.get("/api/bluff/lobbies")
        assert not any(m["id"] == match_id for m in res.json())

    def test_simulated_bot_duel_flow(self, client: TestClient):
        """
        Tests the automated simulated bot duel flow:
        1. Human creates match with secret
        2. Simulated bot joins via /join
        3. Match transitions to DECISION, initial action turn granted to human
        4. Human submits PUSH
        5. Match authoritatively resolves and settles
        """
        # 1. Human creates match
        res = client.post(
            "/api/bluff/create",
            json={"creator_id": "0xhuman_hero", "stake_amount": "5.0", "secret_value": 9},
        )
        assert res.status_code == 201
        match_id = res.json()["id"]

        # 2. Simulated bot joins
        bot_id = "0xsimulated_duelist_42"
        res = client.post(
            f"/api/bluff/match/{match_id}/join",
            json={"player_id": bot_id, "secret_value": 3},
        )
        assert res.status_code == 200
        join_data = res.json()
        assert join_data["status"] == "DECISION"
        assert join_data["opponent"]["player_id"] == bot_id
        assert join_data["active_turn_player_id"] == "0xhuman_hero"

        # 3. Human perspective check
        res = client.get(f"/api/bluff/match/{match_id}?player_id=0xhuman_hero")
        assert res.status_code == 200
        human_view = res.json()
        assert human_view["can_act"] is True
        assert human_view["creator"]["secret_value"] == 9
        assert human_view["opponent"]["secret_value"] is None  # Bot secret masked

        # 4. Human pushes
        res = client.post(
            f"/api/bluff/match/{match_id}/decision",
            json={"player_id": "0xhuman_hero", "action": "PUSH"},
        )
        assert res.status_code == 200
        resolved_data = res.json()
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["winner_id"] == "0xhuman_hero"
        assert resolved_data["resolution_reason"] == "SHOWDOWN_HIGHER_CARD"
        assert resolved_data["payout_tx_hash"] is not None

