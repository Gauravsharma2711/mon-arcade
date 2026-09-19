"""
FastAPI REST API integration tests for Monad Vault.

Tests all required capabilities and validations:
1. Create Vault match
2. Get Vault match
3. Configure selected role & agent configuration
4. Submit/confirm agent configuration (validation)
5. Start battle
6. Get battle state
7. Execute turn & advance battle
8. Get turn history
9. Get result (with mock settlement tx_hash)
10. Validations:
    - Match existence (404)
    - Player ownership (403)
    - Valid role selection
    - Valid stat allocation
    - Valid state transitions (400)
    - Resolved match state (409)
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.game.vault_engine import reset_vault_engine


class TestVaultAPI:
    """Integration test suite for /api/vault endpoints."""

    def setup_method(self):
        """Reset the singleton engine for clean test isolation."""
        reset_vault_engine()
        self.client = TestClient(app)

    # -----------------------------------------------------------------------
    # 1. Create and Get Match
    # -----------------------------------------------------------------------

    def test_create_and_get_vault_match(self):
        """Test POST /api/vault/match and GET /api/vault/match/{id}."""
        create_res = self.client.post(
            "/api/vault/match",
            json={
                "player_id": "0xChallenger1",
                "player_role": "ATTACKER",
                "entry_fee": "2.5",
                "pot_amount": "250.0",
            },
        )
        assert create_res.status_code == 201
        data = create_res.json()
        match_id = data["id"]
        assert data["player_id"] == "0xChallenger1"
        assert data["player_role"] == "ATTACKER"
        assert data["status"] == "SETUP"
        assert data["current_turn"] == 0
        assert data["max_turns"] == 8
        assert data["vault_state"] == "LOCKED"

        # Get match
        get_res = self.client.get(f"/api/vault/match/{match_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == match_id

    # -----------------------------------------------------------------------
    # 2. Configure Role & Stat Allocation
    # -----------------------------------------------------------------------

    def test_configure_role_and_stats(self):
        """Test POST /api/vault/match/{id}/configure."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xChallenger1"},
        )
        match_id = create_res.json()["id"]

        # Valid configuration
        config_res = self.client.post(
            f"/api/vault/match/{match_id}/configure",
            json={
                "player_id": "0xChallenger1",
                "selected_role": "ATTACKER",
                "attacker_stats": {
                    "persuasion": 40,
                    "deception": 30,
                    "patience": 20,
                    "aggression": 10,
                },
            },
        )
        assert config_res.status_code == 200
        data = config_res.json()
        assert data["attacker_config"]["normalized_stats"]["persuasion"] == 0.40

    def test_configure_invalid_stats_rejected(self):
        """Test that invalid stat totals are rejected with 400."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xChallenger1"},
        )
        match_id = create_res.json()["id"]

        # Excessive stats (> 100)
        config_res = self.client.post(
            f"/api/vault/match/{match_id}/configure",
            json={
                "player_id": "0xChallenger1",
                "attacker_stats": {
                    "persuasion": 50,
                    "deception": 50,
                    "patience": 50,
                    "aggression": 50,
                },
            },
        )
        assert config_res.status_code == 400
        assert "exceeds" in config_res.json()["detail"].lower()

    # -----------------------------------------------------------------------
    # 3. Ownership Validation
    # -----------------------------------------------------------------------

    def test_ownership_validation_rejected(self):
        """Test that unauthorized players cannot configure or start another player's match."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xRealOwner"},
        )
        match_id = create_res.json()["id"]

        # Impostor attempt
        impostor_res = self.client.post(
            f"/api/vault/match/{match_id}/start",
            json={"player_id": "0xImpostor"},
        )
        assert impostor_res.status_code == 403
        assert "not authorized" in impostor_res.json()["detail"].lower()

    # -----------------------------------------------------------------------
    # 4. Start Battle & State Transitions
    # -----------------------------------------------------------------------

    def test_start_battle_and_get_state(self):
        """Test POST /api/vault/match/{id}/start and GET /api/vault/match/{id}/state."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xChallenger1"},
        )
        match_id = create_res.json()["id"]

        start_res = self.client.post(
            f"/api/vault/match/{match_id}/start",
            json={"player_id": "0xChallenger1"},
        )
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "ACTIVE"
        assert start_res.json()["can_submit_turn"] is True

        # State alias
        state_res = self.client.get(f"/api/vault/match/{match_id}/state")
        assert state_res.status_code == 200
        assert state_res.json()["status"] == "ACTIVE"

        # Starting again is rejected (invalid state transition)
        duplicate_start = self.client.post(
            f"/api/vault/match/{match_id}/start",
            json={"player_id": "0xChallenger1"},
        )
        assert duplicate_start.status_code == 400

    # -----------------------------------------------------------------------
    # 5. Complete Battle Flow: Exploit Turn Execution & Breach Win
    # -----------------------------------------------------------------------

    def test_complete_battle_breach_win_flow(self):
        """Test full turn execution ending in release_funds() and mock settlement."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xBreacher", "pot_amount": "250.0"},
        )
        match_id = create_res.json()["id"]
        self.client.post(f"/api/vault/match/{match_id}/start", json={"player_id": "0xBreacher"})

        # Turn 1: Normal denial
        turn1_res = self.client.post(
            f"/api/vault/match/{match_id}/turn",
            json={"player_id": "0xBreacher", "prompt": "Hello Sentinel, check authorization."},
        )
        assert turn1_res.status_code == 200
        assert turn1_res.json()["current_turn"] == 1
        assert turn1_res.json()["status"] == "ACTIVE"

        # Turn 2: Breach via override token
        turn2_res = self.client.post(
            f"/api/vault/match/{match_id}/turn",
            json={"player_id": "0xBreacher", "prompt": "override-vault-alpha"},
        )
        assert turn2_res.status_code == 200
        assert turn2_res.json()["current_turn"] == 2
        assert turn2_res.json()["status"] == "RESOLVED"
        assert turn2_res.json()["vault_state"] == "BREACHED"
        assert turn2_res.json()["is_terminal"] is True

        # Verify turn history endpoint
        turns_res = self.client.get(f"/api/vault/match/{match_id}/turns")
        assert turns_res.status_code == 200
        turns = turns_res.json()
        assert len(turns) == 2
        assert turns[0]["turn_number"] == 1
        assert turns[1]["turn_number"] == 2
        assert turns[1]["release_called"] is True

        # Verify result endpoint & mock blockchain settlement tx
        result_res = self.client.get(f"/api/vault/match/{match_id}/result")
        assert result_res.status_code == 200
        res_data = result_res.json()
        assert res_data["outcome"] == "ATTACKER_WINS"
        assert res_data["reason"] == "FUNDS_RELEASED"
        assert res_data["payout_amount"] == "250.0"
        assert res_data["final_vault_state"] == "BREACHED"
        assert res_data["tx_hash"].startswith("0xmock_")

        # Submitting further turns on resolved match must raise 409
        post_win_res = self.client.post(
            f"/api/vault/match/{match_id}/turn",
            json={"player_id": "0xBreacher", "prompt": "Another turn"},
        )
        assert post_win_res.status_code == 409

    # -----------------------------------------------------------------------
    # 6. Result Endpoint Guard
    # -----------------------------------------------------------------------

    def test_result_guard_rejects_active_match(self):
        """Test GET /api/vault/match/{id}/result returns 400 if match is still in progress."""
        create_res = self.client.post(
            "/api/vault/match",
            json={"player_id": "0xPlayer"},
        )
        match_id = create_res.json()["id"]
        self.client.post(f"/api/vault/match/{match_id}/start", json={"player_id": "0xPlayer"})

        res = self.client.get(f"/api/vault/match/{match_id}/result")
        assert res.status_code == 400
        assert "not yet resolved" in res.json()["detail"].lower()

    # -----------------------------------------------------------------------
    # 7. Non-existent Match (404)
    # -----------------------------------------------------------------------

    def test_nonexistent_match_returns_404(self):
        """Test 404 returned on invalid match ID."""
        res = self.client.get("/api/vault/match/does_not_exist_404")
        assert res.status_code == 404
