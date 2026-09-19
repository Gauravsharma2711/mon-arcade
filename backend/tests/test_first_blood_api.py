"""
Backend test suite for First Blood / Early Arcade Player.
Verifies:
- First player record is created on initial participation
- Original first_participation_at is preserved
- Never duplicates record on subsequent participations
- Player number is preserved and incremental
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_record_first_blood_new_player():
    """Verify first participation creates a record with is_first_time=True."""
    wallet = "0xFirstTimeHero1111111111111111111111111111"
    resp = client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "VAULT"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["wallet"] == wallet
    assert data["is_first_time"] is True
    assert data["first_game"] == "VAULT"
    assert data["first_participation_at"] is not None
    assert data["player_number"] is not None
    assert data["player_number"] >= 1


def test_record_first_blood_preserves_timestamp_and_does_not_duplicate():
    """Verify subsequent participations preserve the original timestamp and is_first_time=False."""
    wallet = "0xRepeatGamer22222222222222222222222222222"
    # First play
    first_resp = client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "BLUFF"},
    )
    assert first_resp.status_code == 200
    first_data = first_resp.json()
    orig_ts = first_data["first_participation_at"]
    orig_num = first_data["player_number"]
    assert first_data["is_first_time"] is True

    # Second play
    second_resp = client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "VAULT"},
    )
    assert second_resp.status_code == 200
    second_data = second_resp.json()

    assert second_data["wallet"] == wallet
    assert second_data["is_first_time"] is False
    # Preserves original timestamp and player number
    assert second_data["first_participation_at"] == orig_ts
    assert second_data["player_number"] == orig_num
    assert second_data["first_game"] == "BLUFF"  # Original game kept


def test_get_first_blood_record():
    """Verify querying an existing wallet's early player record."""
    wallet = "0xQueryWallet33333333333333333333333333333"
    client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "VAULT"},
    )

    get_resp = client.get(f"/api/first-blood/{wallet}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["wallet"] == wallet
    assert data["player_number"] is not None

    # Query non-existent wallet
    bad_resp = client.get("/api/first-blood/0xDoesNotExist99999999999999999999999")
    assert bad_resp.status_code == 404
