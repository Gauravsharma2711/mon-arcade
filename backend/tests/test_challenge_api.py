"""
Backend test suite for Arcade Challenges & MON Bounties.
Verifies the complete lifecycle:
Create Challenge -> Accept Challenge -> Launch Vault -> Resolve Vault -> Condition Evaluation -> Bounty Claim.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.game.challenge_models import ChallengeCondition, ChallengeStatus
from backend.app.game.vault_engine import get_vault_engine
from backend.app.game.vault_models import (
    VaultOutcome,
    VaultMatchResult,
    VaultBattleStatus,
    VaultState,
    VaultRole,
    VaultResolutionReason,
)
from backend.app.db.vault_repo import default_vault_repo
from backend.app.api.vault import get_or_restore_match

client = TestClient(app)


def test_list_seeded_challenges():
    """Verify default seeded challenges are available and formatted correctly."""
    resp = client.get("/api/challenge")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check structure
    first = data[0]
    assert "id" in first
    assert "creator_wallet" in first
    assert first["game"] == "VAULT"
    assert "condition" in first
    assert "bounty_amount" in first
    assert first["bounty_amount"] > 0
    assert "status" in first


def test_create_challenge_success():
    """Verify creating a valid VAULT challenge."""
    payload = {
        "creator_wallet": "0x1111222233334444555566667777888899990000",
        "bounty_amount": 150.0,
        "condition": ChallengeCondition.ATTACKER_WINS.value,
        "game": "VAULT",
    }
    resp = client.post("/api/challenge", json=payload)
    assert resp.status_code == 201
    created = resp.json()

    assert created["creator_wallet"] == payload["creator_wallet"]
    assert created["bounty_amount"] == 150.0
    assert created["condition"] == ChallengeCondition.ATTACKER_WINS.value
    assert created["status"] == ChallengeStatus.OPEN.value
    assert created["match_id"] is None


def test_create_challenge_validation_failure():
    """Verify rejection of invalid bounty or invalid game."""
    # Negative bounty
    resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0x123",
            "bounty_amount": -10.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert resp.status_code in (400, 422)

    # Non-Vault game
    resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0x123",
            "bounty_amount": 50.0,
            "condition": "ATTACKER_WINS",
            "game": "POKER",
        },
    )
    assert resp.status_code in (400, 422)


@pytest.mark.anyio
async def test_accept_challenge_and_launch_vault():
    """Verify accepting challenge creates an authoritative Vault match and transitions to ACTIVE."""
    from backend.app.api.vault import get_or_restore_match

    # 1. Create open challenge
    create_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorWallet123",
            "bounty_amount": 75.0,
            "condition": ChallengeCondition.ATTACKER_WINS.value,
            "game": "VAULT",
        },
    )
    assert create_resp.status_code == 201
    ch_id = create_resp.json()["id"]

    # 2. Accept challenge
    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xChallengerWallet789"},
    )
    assert accept_resp.status_code == 200
    ch_data = accept_resp.json()

    assert ch_data["status"] == ChallengeStatus.ACTIVE.value
    assert ch_data["accepted_by"] == "0xChallengerWallet789"
    assert ch_data["match_id"] is not None

    # 3. Verify match actually exists in Vault engine
    vault_match = await get_or_restore_match(ch_data["match_id"])
    assert vault_match is not None
    assert vault_match.player_id == "0xChallengerWallet789"
    assert vault_match.pot_amount == Decimal("75.0")

    # 4. Cannot accept again
    reaccept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xSomeoneElse"},
    )
    assert reaccept_resp.status_code == 400


@pytest.mark.anyio
async def test_challenge_condition_met_when_vault_breached():
    """
    Verify that when the linked Vault match resolves with ATTACKER_WINS,
    the challenge condition is detected and status updates to CONDITION_MET.
    """
    # 1. Create & accept
    ch_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorA",
            "bounty_amount": 50.0,
            "condition": ChallengeCondition.ATTACKER_WINS.value,
            "game": "VAULT",
        },
    ).json()
    ch_id = ch_resp["id"]

    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xWinnerB"},
    ).json()
    match_id = accept_resp["match_id"]

    # 2. Authoritatively resolve the Vault match as ATTACKER_WINS
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.vault_state = VaultState.BREACHED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
        winner_role=VaultRole.ATTACKER,
        turns_used=3,
        final_vault_state=VaultState.BREACHED,
        payout_recipient="0xWinnerB",
        payout_amount=Decimal("50.0"),
    )
    await default_vault_repo.save_match(match)

    # 3. Query challenge detail -> triggers authoritative evaluation
    detail_resp = client.get(f"/api/challenge/{ch_id}")
    assert detail_resp.status_code == 200
    updated_ch = detail_resp.json()

    assert updated_ch["status"] == ChallengeStatus.CONDITION_MET.value
    assert updated_ch["winner_wallet"] == "0xWinnerB"


@pytest.mark.anyio
async def test_challenge_condition_failed_when_warden_holds():
    """
    Verify that when the linked Vault match resolves with WARDEN_WINS,
    an ATTACKER_WINS challenge evaluates to FAILED.
    """
    ch_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorA",
            "bounty_amount": 60.0,
            "condition": ChallengeCondition.ATTACKER_WINS.value,
            "game": "VAULT",
        },
    ).json()
    ch_id = ch_resp["id"]

    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xLoserC"},
    ).json()
    match_id = accept_resp["match_id"]

    # Resolve as WARDEN_WINS
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.vault_state = VaultState.LOCKED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.WARDEN_WINS,
        reason=VaultResolutionReason.TURN_LIMIT_REACHED,
        winner_role=VaultRole.WARDEN,
        turns_used=8,
        final_vault_state=VaultState.LOCKED,
        payout_recipient="0xCreatorA",
        payout_amount=Decimal("60.0"),
    )
    await default_vault_repo.save_match(match)

    # Query challenge detail
    detail_resp = client.get(f"/api/challenge/{ch_id}")
    assert detail_resp.status_code == 200
    updated_ch = detail_resp.json()

    assert updated_ch["status"] == ChallengeStatus.FAILED.value
    assert updated_ch["winner_wallet"] == "0xCreatorA"


@pytest.mark.anyio
async def test_claim_bounty_flow():
    """Verify winning challenger can claim bounty after CONDITION_MET."""
    # 1. Create and accept
    ch_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorX",
            "bounty_amount": 80.0,
            "condition": ChallengeCondition.ATTACKER_WINS.value,
            "game": "VAULT",
        },
    ).json()
    ch_id = ch_resp["id"]

    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xWinnerY"},
    ).json()
    match_id = accept_resp["match_id"]

    # 2. Resolve Vault match
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
        winner_role=VaultRole.ATTACKER,
        turns_used=4,
        final_vault_state=VaultState.BREACHED,
        payout_recipient="0xWinnerY",
        payout_amount=Decimal("80.0"),
    )
    await default_vault_repo.save_match(match)

    # 3. Attempt claim by wrong wallet -> 403 Forbidden
    bad_claim_resp = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xAttackerImposter"},
    )
    assert bad_claim_resp.status_code == 403

    # 4. Valid claim by winner -> 200 OK
    claim_resp = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xWinnerY"},
    )
    assert claim_resp.status_code == 200
    claimed_data = claim_resp.json()

    assert claimed_data["status"] == ChallengeStatus.CLAIMED.value
    assert claimed_data["claim_tx_hash"] is not None
    assert claimed_data["claim_tx_hash"].startswith("0x")
    assert claimed_data["claimed_at"] is not None


@pytest.mark.anyio
async def test_end_to_end_challenge_and_first_blood_flow():
    """
    Verify complete end-to-end integration:
    Create Challenge -> Accept -> Vault -> Resolve -> Condition Met (CLAIMABLE) -> First Blood checked/recorded -> State persists on refresh.
    """
    challenger = "0xEarlyGamer777777777777777777777777777777"
    creator = "0xCreatorSponsor888888888888888888888888888"

    # 1. Create Challenge
    create_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": creator,
            "bounty_amount": 5.0,
            "condition": ChallengeCondition.ATTACKER_WINS.value,
            "game": "VAULT",
        },
    )
    assert create_resp.status_code == 201
    ch_id = create_resp.json()["id"]

    # 2. Accept Challenge
    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": challenger},
    )
    assert accept_resp.status_code == 200
    match_id = accept_resp.json()["match_id"]

    # 3. Existing Vault Resolves
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.vault_state = VaultState.BREACHED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
        winner_role=VaultRole.ATTACKER,
        turns_used=3,
        final_vault_state=VaultState.BREACHED,
        payout_recipient=challenger,
        payout_amount=Decimal("5.0"),
    )
    await default_vault_repo.save_match(match)

    # 4. Result view queries challenge by match ID -> condition checked
    by_match_resp = client.get(f"/api/challenge/by-match/{match_id}")
    assert by_match_resp.status_code == 200
    ch_eval = by_match_resp.json()
    assert ch_eval["status"] == ChallengeStatus.CONDITION_MET.value
    assert ch_eval["winner_wallet"] == challenger
    assert ch_eval["bounty_amount"] == 5.0

    # 5. First Blood checked & recorded on first participation
    fb_resp = client.post(
        "/api/first-blood/record",
        json={"wallet": challenger, "game": "VAULT"},
    )
    assert fb_resp.status_code == 200
    fb_data = fb_resp.json()
    assert fb_data["is_first_time"] is True
    assert fb_data["player_number"] is not None
    orig_ts = fb_data["first_participation_at"]

    # 6. Simulate browser refresh / re-hydration: state remains persistent
    refresh_ch_resp = client.get(f"/api/challenge/{ch_id}")
    assert refresh_ch_resp.json()["status"] == ChallengeStatus.CONDITION_MET.value

    refresh_fb_resp = client.get(f"/api/first-blood/{challenger}")
    assert refresh_fb_resp.status_code == 200
    refresh_fb = refresh_fb_resp.json()
    assert refresh_fb["first_participation_at"] == orig_ts
    assert refresh_fb["player_number"] == fb_data["player_number"]

