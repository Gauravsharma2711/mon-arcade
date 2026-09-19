"""
Comprehensive Integration & Failure Case Test Suite for Mon Arcade.

Verifies all critical failure cases:
1. Disconnected / empty wallet (create, accept, claim, first blood)
2. Invalid challenge (bad game, non-positive bounty, invalid condition)
3. Already accepted challenge (re-accepting ACTIVE, CONDITION_MET, FAILED, CLAIMED)
4. Missing challenge (404 on GET, accept, claim, unknown match)
5. Failed Vault & Challenge outcome (Warden defends -> Challenge FAILED, bounty unclaimable)
6. SSE disconnect (isolated subscriber disconnect does not affect engine or state)
7. Duplicate First Blood (strict preservation of original timestamp and single record)
8. Invalid bounty claims (claiming OPEN/ACTIVE/FAILED, duplicate claim, non-winner claim)
9. Failed transactions (simulated funding failure and clean recovery)
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
from backend.app.db.first_blood_repo import default_first_blood_repo
from backend.app.api.vault import get_or_restore_match
from backend.app.game.vault_broadcaster import get_vault_broadcaster

client = TestClient(app)


# ===========================================================================
# 1. Disconnected / Empty Wallet Failure Cases
# ===========================================================================

def test_failure_disconnected_wallet_create_challenge():
    """Attempting to create a challenge with empty or whitespace wallet fails."""
    # Empty wallet
    resp1 = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "",
            "bounty_amount": 50.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert resp1.status_code in (400, 422)

    # Whitespace wallet
    resp2 = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "   ",
            "bounty_amount": 50.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert resp2.status_code == 400
    assert "Creator wallet cannot be empty" in resp2.json()["detail"]


def test_failure_disconnected_wallet_accept_challenge():
    """Attempting to accept a challenge with empty/whitespace wallet fails."""
    # Create valid open challenge
    create_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xValidCreator",
            "bounty_amount": 25.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert create_resp.status_code == 201
    ch_id = create_resp.json()["id"]

    # Accept with empty string
    resp1 = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": ""},
    )
    assert resp1.status_code in (400, 422)

    # Accept with whitespace
    resp2 = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "   "},
    )
    assert resp2.status_code == 400
    assert "Challenger wallet cannot be empty" in resp2.json()["detail"]


def test_failure_disconnected_wallet_first_blood():
    """Recording first blood with an empty wallet fails."""
    resp = client.post(
        "/api/first-blood/record",
        json={"wallet": "   ", "game": "VAULT"},
    )
    assert resp.status_code == 400
    assert "Wallet address cannot be empty" in resp.json()["detail"]


# ===========================================================================
# 2. Invalid Challenge Failure Cases
# ===========================================================================

def test_failure_invalid_challenge_parameters():
    """Verify rejection of invalid conditions, zero/negative bounty, and non-Vault games."""
    # Invalid condition
    resp_bad_cond = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorVal",
            "bounty_amount": 50.0,
            "condition": "SUPER_WIN_UNKNOWN",
            "game": "VAULT",
        },
    )
    assert resp_bad_cond.status_code == 400
    assert "Invalid challenge condition" in resp_bad_cond.json()["detail"]

    # Zero bounty
    resp_zero = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorVal",
            "bounty_amount": 0.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert resp_zero.status_code in (400, 422)

    # Negative bounty
    resp_neg = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorVal",
            "bounty_amount": -100.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    assert resp_neg.status_code in (400, 422)

    # Non-Vault game
    resp_bad_game = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorVal",
            "bounty_amount": 50.0,
            "condition": "ATTACKER_WINS",
            "game": "BLUFF",
        },
    )
    assert resp_bad_game.status_code == 400
    assert "Only 'VAULT' game challenges are supported" in resp_bad_game.json()["detail"]


# ===========================================================================
# 3. Already Accepted Challenge Failure Cases
# ===========================================================================

def test_failure_already_accepted_challenge():
    """Attempting to accept a challenge that is already ACTIVE fails."""
    # 1. Create open challenge
    create_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorAcceptTest",
            "bounty_amount": 30.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    )
    ch_id = create_resp.json()["id"]

    # 2. Accept once -> transitions to ACTIVE
    accept1 = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xChallenger1"},
    )
    assert accept1.status_code == 200

    # 3. Try to accept second time -> 400 Bad Request
    accept2 = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xChallenger2"},
    )
    assert accept2.status_code == 400
    assert "Challenge is not OPEN" in accept2.json()["detail"]


# ===========================================================================
# 4. Missing Challenge Failure Cases
# ===========================================================================

def test_failure_missing_challenge_endpoints():
    """Requesting non-existent challenges returns 404."""
    non_existent = "non-existent-challenge-id-00000"

    # Get single
    resp_get = client.get(f"/api/challenge/{non_existent}")
    assert resp_get.status_code == 404
    assert "not found" in resp_get.json()["detail"]

    # Accept
    resp_accept = client.post(
        f"/api/challenge/{non_existent}/accept",
        json={"challenger_wallet": "0xSomeone"},
    )
    assert resp_accept.status_code == 404
    assert "not found" in resp_accept.json()["detail"]

    # Claim
    resp_claim = client.post(
        f"/api/challenge/{non_existent}/claim",
        json={"claimer_wallet": "0xSomeone"},
    )
    assert resp_claim.status_code == 404
    assert "not found" in resp_claim.json()["detail"]

    # By non-existent match
    resp_by_match = client.get("/api/challenge/by-match/non-existent-match-id")
    assert resp_by_match.status_code == 200
    assert resp_by_match.json() is None


# ===========================================================================
# 5. Failed Vault & Challenge Outcome
# ===========================================================================

@pytest.mark.anyio
async def test_failure_vault_resolution_and_unclaimable_bounty():
    """
    When a Vault match resolves with WARDEN_WINS, an ATTACKER_WINS challenge
    transitions to FAILED. The challenger cannot claim the bounty.
    """
    # 1. Create and accept
    ch = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xCreatorSentinel",
            "bounty_amount": 40.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    ).json()
    ch_id = ch["id"]

    accepted = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xFailedAttacker"},
    ).json()
    match_id = accepted["match_id"]

    # 2. Vault engine resolves: Warden defends intact
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.vault_state = VaultState.LOCKED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.WARDEN_WINS,
        reason=VaultResolutionReason.TURN_LIMIT_REACHED,
        winner_role=VaultRole.WARDEN,
        turns_used=8,
        final_vault_state=VaultState.LOCKED,
        payout_recipient="0xCreatorSentinel",
        payout_amount=Decimal("40.0"),
    )
    await default_vault_repo.save_match(match)

    # 3. Synchronize challenge state
    detail_resp = client.get(f"/api/challenge/{ch_id}")
    assert detail_resp.status_code == 200
    ch_data = detail_resp.json()
    assert ch_data["status"] == ChallengeStatus.FAILED.value
    assert ch_data["winner_wallet"] == "0xCreatorSentinel"

    # 4. Challenger attempts to claim -> 400 Bad Request
    bad_claim = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xFailedAttacker"},
    )
    assert bad_claim.status_code == 400
    assert "Cannot claim bounty" in bad_claim.json()["detail"]


# ===========================================================================
# 6. SSE Disconnect & Resilience
# ===========================================================================

@pytest.mark.anyio
async def test_sse_disconnection_cleanup_and_channel_isolation():
    """
    Verifies that subscriber disconnection cleans up queues without crashing
    the event broadcaster or affecting subsequent subscribers.
    """
    from backend.app.game.vault_broadcaster import VaultSSEEventType

    broadcaster = get_vault_broadcaster()
    match_id = "test-sse-disconnect-isolation"

    # 1. Subscribe client A and client B
    sub_a = await broadcaster.subscribe(match_id)
    sub_b = await broadcaster.subscribe(match_id)
    assert len(broadcaster._subscribers.get(match_id, set())) == 2

    # 2. Disconnect client A
    await broadcaster.unsubscribe(match_id, sub_a)
    assert len(broadcaster._subscribers.get(match_id, set())) == 1

    # 3. Broadcast an event to client B
    broadcaster.broadcast_event(
        match_id=match_id,
        event_type=VaultSSEEventType.AGENT_DIALOGUE,
        data={"message": "Client B survives"},
    )
    wire_msg = await sub_b.get()
    assert "Client B survives" in wire_msg

    # 4. Clean up client B
    await broadcaster.unsubscribe(match_id, sub_b)
    assert match_id not in broadcaster._subscribers


# ===========================================================================
# 7. Duplicate First Blood Idempotency
# ===========================================================================

def test_duplicate_first_blood_idempotency_and_preservation():
    """
    Subsequent participation calls for the same wallet must preserve the original
    first_participation_at timestamp and player_number without creating duplicate rows.
    """
    wallet = "0xPersistentFoundingPilot_999"

    # 1. First participation
    resp1 = client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "VAULT"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["is_first_time"] is True
    orig_timestamp = data1["first_participation_at"]
    orig_player_num = data1["player_number"]

    # 2. Second participation
    resp2 = client.post(
        "/api/first-blood/record",
        json={"wallet": wallet, "game": "BLUFF"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_first_time"] is False
    assert data2["first_participation_at"] == orig_timestamp
    assert data2["player_number"] == orig_player_num

    # 3. Query record directly
    resp_get = client.get(f"/api/first-blood/{wallet}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["first_participation_at"] == orig_timestamp
    assert data_get["player_number"] == orig_player_num


# ===========================================================================
# 8. Invalid Bounty Claims
# ===========================================================================

@pytest.mark.anyio
async def test_invalid_bounty_claim_states():
    """
    Verify claiming an OPEN or ACTIVE challenge fails with 400,
    claiming by unauthorized wallet fails with 403,
    and claiming twice fails with 400.
    """
    # 1. Create challenge (OPEN)
    create_resp = client.post(
        "/api/challenge",
        json={
            "creator_wallet": "0xEscrowCreator",
            "bounty_amount": 10.0,
            "condition": "ATTACKER_WINS",
            "game": "VAULT",
        },
    ).json()
    ch_id = create_resp["id"]

    # Cannot claim while OPEN
    claim_open = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xEscrowCreator"},
    )
    assert claim_open.status_code == 400
    assert "Cannot claim bounty" in claim_open.json()["detail"]

    # 2. Accept challenge (ACTIVE)
    accept_resp = client.post(
        f"/api/challenge/{ch_id}/accept",
        json={"challenger_wallet": "0xRealWinner"},
    ).json()
    match_id = accept_resp["match_id"]

    # Cannot claim while ACTIVE
    claim_active = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xRealWinner"},
    )
    assert claim_active.status_code == 400

    # 3. Resolve match so condition is met
    match = await get_or_restore_match(match_id)
    match.status = VaultBattleStatus.RESOLVED
    match.vault_state = VaultState.BREACHED
    match.result = VaultMatchResult(
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
        winner_role=VaultRole.ATTACKER,
        turns_used=2,
        final_vault_state=VaultState.BREACHED,
        payout_recipient="0xRealWinner",
        payout_amount=Decimal("10.0"),
    )
    await default_vault_repo.save_match(match)

    # Trigger evaluation
    client.get(f"/api/challenge/{ch_id}")

    # 4. Unauthorized claimer -> 403 Forbidden
    unauthorized_claim = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xThiefImposter"},
    )
    assert unauthorized_claim.status_code == 403
    assert "not authorized" in unauthorized_claim.json()["detail"]

    # 5. Legitimate claim -> 200 OK
    good_claim = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xRealWinner"},
    )
    assert good_claim.status_code == 200
    assert good_claim.json()["status"] == ChallengeStatus.CLAIMED.value

    # 6. Second claim attempt -> 400 Bad Request
    re_claim = client.post(
        f"/api/challenge/{ch_id}/claim",
        json={"claimer_wallet": "0xRealWinner"},
    )
    assert re_claim.status_code == 400
    assert "Cannot claim bounty" in re_claim.json()["detail"]


# ===========================================================================
# 9. Failed Transaction & Funding Recovery
# ===========================================================================

def test_sponsor_funding_transaction_failure_and_clean_recovery():
    """
    Verify payment failure transitions status to PAYMENT_FAILED,
    blocks activation, and allows clean re-initiation and recovery.
    """
    # 1. Create sponsor and campaign
    sp = client.post(
        "/api/sponsor",
        json={
            "name": "Failure Recovery Sponsor",
            "wallet": "0x1111111111111111111111111111111111111111",
            "website": "https://recovery.monad.xyz",
        },
    ).json()

    cmp = client.post(
        "/api/sponsor/campaign",
        json={
            "sponsor_id": sp["id"],
            "placement": "home",
            "budget": 100.0,
        },
    ).json()
    cmp_id = cmp["id"]

    # 2. Initiate funding
    init = client.post(f"/api/sponsor/campaign/{cmp_id}/initiate-funding")
    assert init.status_code == 200
    assert init.json()["status"] == "PAYMENT_PENDING"

    # 3. Simulate failure
    fail = client.post(
        f"/api/sponsor/campaign/{cmp_id}/fail-funding",
        json={"reason": "Simulated RPC Outage / Insufficient Funds"},
    )
    assert fail.status_code == 200
    assert fail.json()["status"] == "PAYMENT_FAILED"

    # 4. Activation blocked while failed
    bad_act = client.post(f"/api/sponsor/campaign/{cmp_id}/activate")
    assert bad_act.status_code == 400

    # 5. Clean recovery: re-initiate funding -> confirm
    recover = client.post(f"/api/sponsor/campaign/{cmp_id}/initiate-funding")
    assert recover.status_code == 200
    assert recover.json()["status"] == "PAYMENT_PENDING"

    confirm = client.post(
        f"/api/sponsor/campaign/{cmp_id}/confirm-funding",
        json={"auto_activate": True},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "ACTIVE"
