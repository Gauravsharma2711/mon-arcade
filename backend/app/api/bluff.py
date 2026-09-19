"""
FastAPI REST API Router for Bluff or Bust.

Endpoints:
1. POST /api/bluff/create           - Create a new duel
2. GET  /api/bluff/match/{id}       - Get sanitized match state
3. GET  /api/bluff/lobbies          - List open lobbies
4. POST /api/bluff/match/{id}/join  - Join an existing duel
5. POST /api/bluff/match/{id}/commit - Submit secret commitment
6. POST /api/bluff/match/{id}/decision - Submit Push or Fold action
7. POST /api/bluff/match/{id}/reveal - Authoritatively reveal & verify
8. GET  /api/bluff/match/{id}/result - Get final resolved showdown & result
9. POST /api/bluff/match/{id}/cancel - Cancel an open match

All authoritative logic is delegated to BluffGameEngine.
Strict sanitization ensures hidden values/salts are never leaked prematurely.
"""

from decimal import Decimal
from typing import Optional, List, Union
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffMatchClientView,
    BluffMatchResult,
)
from backend.app.game.bluff_engine import (
    get_bluff_engine,
    BluffEngineError,
    MatchNotFoundError,
    InvalidStateTransitionError,
    UnauthorizedPlayerError,
    InvalidDecisionError,
    InvalidSecretValueError,
    CommitmentVerificationError,
    MatchAlreadyResolvedError,
)

router = APIRouter(prefix="/bluff", tags=["bluff"])


# ============================================================================
# Request Schemas
# ============================================================================

class CreateBluffMatchRequest(BaseModel):
    creator_id: str = Field(..., min_length=1, description="Player wallet or ID creating the match")
    stake_amount: Decimal = Field(Decimal("5.0"), gt=Decimal("0"), description="Stake in MON")
    secret_value: Optional[int] = Field(None, ge=1, le=10, description="Hidden card value 1-10")
    salt: Optional[str] = Field(None, description="Optional custom salt; engine generates random salt if None")
    turn_seconds: int = Field(15, ge=5, le=60, description="Turn countdown duration in seconds")


class JoinBluffMatchRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Opponent wallet or ID joining the duel")
    secret_value: Optional[int] = Field(None, ge=1, le=10, description="Hidden card value 1-10")
    salt: Optional[str] = Field(None, description="Optional custom salt")


class CommitBluffSecretRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Participant committing secret value")
    secret_value: int = Field(..., ge=1, le=10, description="Hidden card value 1-10")
    salt: Optional[str] = Field(None, description="Optional custom salt")


class BluffActionRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Active player submitting action")
    action: Union[BluffAction, str] = Field(..., description="Action to submit: PUSH or FOLD")


class RevealBluffRequest(BaseModel):
    player_id: Optional[str] = Field(None, description="Optional player requesting or verifying reveal")


class CancelBluffMatchRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Creator ID requesting lobby cancellation")


# ============================================================================
# Exception Handler Helper
# ============================================================================

def _handle_engine_error(e: Exception) -> None:
    """Map domain engine exceptions to precise HTTP error codes and messages."""
    if isinstance(e, MatchNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, UnauthorizedPlayerError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    elif isinstance(e, (InvalidDecisionError, InvalidSecretValueError)):
        raise HTTPException(status_code=422, detail=str(e))
    elif isinstance(e, MatchAlreadyResolvedError):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(e))
    elif isinstance(e, CommitmentVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, InvalidStateTransitionError):
        msg = str(e).lower()
        if "already" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, BluffEngineError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/create", response_model=BluffMatchClientView, status_code=status.HTTP_201_CREATED)
async def create_match(req: CreateBluffMatchRequest):
    """
    1. Create Match.
    Initializes a new duel with creator stake and optional secret value commitment.
    Returns sanitized client view for the creator.
    """
    engine = get_bluff_engine()
    try:
        match = engine.create_match(
            creator_id=req.creator_id,
            stake_amount=req.stake_amount,
            secret_value=req.secret_value,
            salt=req.salt,
            turn_seconds=req.turn_seconds,
        )
        return match.to_client_view(viewer_id=req.creator_id)
    except Exception as e:
        _handle_engine_error(e)


@router.get("/match/{match_id}", response_model=BluffMatchClientView)
async def get_match(
    match_id: str,
    player_id: Optional[str] = Query(None, description="Requesting player ID for view sanitization"),
):
    """
    2. Get Match.
    Returns sanitized state. Opponent hidden secrets are strictly masked until RESOLVED.
    """
    engine = get_bluff_engine()
    try:
        return engine.get_client_view(match_id=match_id, viewer_id=player_id)
    except Exception as e:
        _handle_engine_error(e)


@router.get("/lobbies", response_model=List[BluffMatchClientView])
async def list_open_lobbies():
    """
    List all open lobbies waiting for an opponent.
    Returns sanitized public view for each open match.
    """
    engine = get_bluff_engine()
    matches = engine.store.list_open_lobbies()
    return [m.to_client_view(viewer_id=None) for m in matches]


@router.post("/match/{match_id}/join", response_model=BluffMatchClientView)
async def join_match(match_id: str, req: JoinBluffMatchRequest):
    """
    3. Join Match.
    An opponent joins an open duel and optionally commits their secret card.
    If both players have committed, the match transitions to DECISION.
    """
    engine = get_bluff_engine()
    try:
        match = engine.join_match(
            match_id=match_id,
            opponent_id=req.player_id,
            secret_value=req.secret_value,
            salt=req.salt,
        )
        return match.to_client_view(viewer_id=req.player_id)
    except Exception as e:
        _handle_engine_error(e)


@router.post("/match/{match_id}/commit", response_model=BluffMatchClientView)
async def submit_commitment(match_id: str, req: CommitBluffSecretRequest):
    """
    4. Submit Commitment.
    Submits a player's hidden secret card (1-10) before the decision phase begins.
    Transitions match to DECISION once both players have committed.
    """
    engine = get_bluff_engine()
    try:
        match = engine.commit_secret(
            match_id=match_id,
            player_id=req.player_id,
            secret_value=req.secret_value,
            salt=req.salt,
        )
        return match.to_client_view(viewer_id=req.player_id)
    except Exception as e:
        _handle_engine_error(e)


@router.post("/match/{match_id}/decision", response_model=BluffMatchClientView)
async def submit_decision(match_id: str, req: BluffActionRequest):
    """
    5. Submit Push/Fold Decision.
    Active player challenges (PUSH) or surrenders (FOLD).
    Triggers authoritative commitment verification and deterministic match resolution.
    """
    engine = get_bluff_engine()
    try:
        match = engine.submit_action(
            match_id=match_id,
            player_id=req.player_id,
            action=req.action,
        )
        return match.to_client_view(viewer_id=req.player_id)
    except Exception as e:
        _handle_engine_error(e)


@router.post("/match/{match_id}/reveal", response_model=BluffMatchResult)
async def reveal_match(match_id: str, req: Optional[RevealBluffRequest] = None):
    """
    6. Reveal.
    Authoritatively reveals secret cards, verifies cryptographic commitments,
    and returns full audit verification and showdown outcome.
    If match has timed out during DECISION, authoritatively resolves by timeout forfeit.
    """
    engine = get_bluff_engine()
    try:
        match = engine.get_match(match_id)

        # If already resolved, return the audited result
        if match.status == BluffMatchStatus.RESOLVED and match.result:
            return match.result

        # If expired in decision phase, trigger timeout resolution
        if match.status == BluffMatchStatus.DECISION:
            if match.is_expired():
                resolved = engine.handle_timeout(match_id)
                if resolved.result:
                    return resolved.result
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Match is currently in DECISION phase. Active player must submit PUSH/FOLD or wait for turn deadline.",
            )

        if match.status in (BluffMatchStatus.WAITING, BluffMatchStatus.ACTIVE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reveal: match is in {match.status.value} phase and has not reached decision showdown.",
            )

        if match.status == BluffMatchStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Match was cancelled.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reveal match in state {match.status.value}.",
        )
    except HTTPException:
        raise
    except Exception as e:
        _handle_engine_error(e)


@router.get("/match/{match_id}/result", response_model=BluffMatchResult)
async def get_match_result(
    match_id: str,
    player_id: Optional[str] = Query(None, description="Optional player requesting result"),
):
    """
    7. Get Result.
    Returns authoritative result structure: winner, loser, revealed values, decisions,
    commitment verification, and settlement status.
    Raises 400 if match is not yet resolved.
    """
    engine = get_bluff_engine()
    try:
        match = engine.get_match(match_id)
        if match.status != BluffMatchStatus.RESOLVED or not match.result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Match {match_id} is not yet resolved (current status: {match.status.value}).",
            )
        return match.result
    except HTTPException:
        raise
    except Exception as e:
        _handle_engine_error(e)


@router.post("/match/{match_id}/cancel", response_model=BluffMatchClientView)
async def cancel_match(match_id: str, req: CancelBluffMatchRequest):
    """
    Cancel Match.
    Creator cancels an open match before an opponent joins.
    """
    engine = get_bluff_engine()
    try:
        match = engine.cancel_match(match_id=match_id, player_id=req.player_id)
        return match.to_client_view(viewer_id=req.player_id)
    except Exception as e:
        _handle_engine_error(e)
