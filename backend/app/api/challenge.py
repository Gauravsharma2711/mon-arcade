"""
Mon Arcade — Challenge & Bounty REST API
Authoritative endpoints for Arcade Challenges / MON Bounties:
1. POST /api/challenge              - Create new challenge
2. GET  /api/challenge              - List challenges (optional status filter)
3. GET  /api/challenge/{id}         - Get challenge detail (evaluates match outcome)
4. POST /api/challenge/{id}/accept  - Accept challenge, launches existing Vault match
5. POST /api/challenge/{id}/claim   - Claim bounty when condition is met
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.game.challenge_models import (
    Challenge,
    ChallengeStatus,
    ChallengeCondition,
    CreateChallengeRequest,
    AcceptChallengeRequest,
    ClaimBountyRequest,
    ChallengeResponse,
    challenge_to_response,
)
from backend.app.db.challenge_repo import default_challenge_repo
from backend.app.game.vault_models import VaultRole, VaultOutcome
from backend.app.game.vault_engine import get_vault_engine
from backend.app.api.vault import get_or_restore_match
from backend.app.blockchain import get_blockchain_service

logger = logging.getLogger("mon_arcade.challenge.api")

router = APIRouter(prefix="/challenge", tags=["challenge"])


async def _evaluate_challenge(challenge: Challenge) -> Challenge:
    """
    Authoritative evaluation connecting existing Vault match result to challenge condition.
    Does not modify Vault winner logic; reads match resolution and determines bounty status.
    """
    if challenge.status != ChallengeStatus.ACTIVE or not challenge.match_id:
        return challenge

    try:
        match = await get_or_restore_match(challenge.match_id)
        if not match.is_terminal or not match.result:
            return challenge

        cond = challenge.condition
        outcome = match.result.outcome

        is_met = False
        if cond in (ChallengeCondition.ATTACKER_WINS.value, "BREACH_VAULT"):
            is_met = (outcome == VaultOutcome.ATTACKER_WINS)
        elif cond == ChallengeCondition.WIN_WITHIN_5_TURNS.value:
            is_met = (outcome == VaultOutcome.ATTACKER_WINS and match.current_turn <= 5)
        elif cond == ChallengeCondition.WARDEN_DEFENDS.value:
            is_met = (outcome == VaultOutcome.WARDEN_WINS)
        else:
            is_met = (outcome.value == cond)

        if is_met:
            challenge.status = ChallengeStatus.CONDITION_MET
            challenge.winner_wallet = challenge.accepted_by
        else:
            challenge.status = ChallengeStatus.FAILED
            challenge.winner_wallet = challenge.creator_wallet

        await default_challenge_repo.save_challenge(challenge)
    except Exception as e:
        logger.warning(f"Error evaluating match '{challenge.match_id}' for challenge '{challenge.id}': {e}")

    return challenge


@router.post("", response_model=ChallengeResponse, status_code=status.HTTP_201_CREATED)
async def create_challenge(req: CreateChallengeRequest):
    """
    Create a new Arcade Challenge with an escrowed MON bounty.
    Only VAULT challenges are supported.
    """
    if not req.creator_wallet.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator wallet cannot be empty.",
        )

    valid_conditions = [c.value for c in ChallengeCondition]
    if req.condition.strip() not in valid_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid challenge condition '{req.condition}'. Must be one of: {valid_conditions}",
        )

    if req.game.upper() != "VAULT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only 'VAULT' game challenges are supported (received '{req.game}').",
        )

    if req.bounty_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bounty amount must be greater than 0 MON.",
        )

    challenge = Challenge(
        creator_wallet=req.creator_wallet.strip(),
        game="VAULT",
        condition=req.condition.strip(),
        bounty_amount=req.bounty_amount,
        status=ChallengeStatus.OPEN,
    )

    await default_challenge_repo.save_challenge(challenge)
    return challenge_to_response(challenge)


@router.get("", response_model=List[ChallengeResponse])
async def list_challenges(
    challenge_status: Optional[ChallengeStatus] = Query(None, alias="status")
):
    """List all challenges, evaluating any active matches before responding."""
    challenges = await default_challenge_repo.list_challenges()

    # Authoritative sync for active challenges
    evaluated = []
    for ch in challenges:
        if ch.status == ChallengeStatus.ACTIVE and ch.match_id:
            ch = await _evaluate_challenge(ch)
        if challenge_status is None or ch.status == challenge_status:
            evaluated.append(challenge_to_response(ch))

    return evaluated


@router.get("/{challenge_id}", response_model=ChallengeResponse)
async def get_challenge(challenge_id: str):
    """Get single challenge detail, synchronizing live Vault result if active."""
    ch = await default_challenge_repo.get_challenge(challenge_id)
    if not ch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{challenge_id}' not found.",
        )

    ch = await _evaluate_challenge(ch)
    return challenge_to_response(ch)


@router.get("/by-match/{match_id}", response_model=Optional[ChallengeResponse])
async def get_challenge_by_match(match_id: str):
    """
    Look up challenge associated with a Vault match ID.
    Authoritatively evaluates condition if match is resolved.
    """
    challenges = await default_challenge_repo.list_challenges()
    for ch in challenges:
        if ch.match_id == match_id:
            ch = await _evaluate_challenge(ch)
            return challenge_to_response(ch)
    return None


@router.post("/{challenge_id}/accept", response_model=ChallengeResponse)
async def accept_challenge(challenge_id: str, req: AcceptChallengeRequest):
    """
    Accept an open challenge.
    Launches a real Vault match in the existing VaultBattleEngine and links it to the challenge.
    """
    if not req.challenger_wallet.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenger wallet cannot be empty.",
        )

    ch = await default_challenge_repo.get_challenge(challenge_id)
    if not ch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{challenge_id}' not found.",
        )

    ch = await _evaluate_challenge(ch)
    if ch.status != ChallengeStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Challenge is not OPEN (current status: {ch.status.value}).",
        )

    # Launch existing Vault match
    engine = get_vault_engine()
    player_role = (
        VaultRole.WARDEN
        if ch.condition == ChallengeCondition.WARDEN_DEFENDS.value
        else VaultRole.ATTACKER
    )

    match = engine.create_match(
        player_id=req.challenger_wallet.strip(),
        player_role=player_role,
        pot_amount=Decimal(str(ch.bounty_amount)),
    )

    ch.accepted_by = req.challenger_wallet.strip()
    ch.match_id = match.id
    ch.status = ChallengeStatus.ACTIVE
    await default_challenge_repo.save_challenge(ch)

    return challenge_to_response(ch)


@router.post("/{challenge_id}/claim", response_model=ChallengeResponse)
async def claim_bounty(challenge_id: str, req: ClaimBountyRequest):
    """
    Claim bounty for a challenge where the condition was met.
    Settles via BlockchainService and marks status as CLAIMED.
    """
    if not req.claimer_wallet.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claimer wallet cannot be empty.",
        )

    ch = await default_challenge_repo.get_challenge(challenge_id)
    if not ch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{challenge_id}' not found.",
        )

    ch = await _evaluate_challenge(ch)
    if ch.status != ChallengeStatus.CONDITION_MET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot claim bounty. Current status: '{ch.status.value}', expected 'CONDITION_MET'.",
        )

    if req.claimer_wallet.strip().lower() != (ch.winner_wallet or "").strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Wallet '{req.claimer_wallet}' is not authorized to claim this bounty. Winner is '{ch.winner_wallet}'.",
        )

    bc = get_blockchain_service()
    tx_data = await bc.submit_transaction(
        tx_type="BOUNTY_CLAIM",
        user_id=req.claimer_wallet.strip(),
        amount=float(ch.bounty_amount),
    )

    ch.status = ChallengeStatus.CLAIMED
    ch.claimed_at = datetime.now(timezone.utc)
    ch.claim_tx_hash = tx_data.get("tx_hash")
    await default_challenge_repo.save_challenge(ch)

    return challenge_to_response(ch)
