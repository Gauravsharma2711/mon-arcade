"""
FastAPI REST API Router for Monad Vault.

Authoritative endpoints for the Vault Intrusion Chamber:
1. POST /api/vault/match              - Create a new Vault match
2. GET  /api/vault/match/{id}         - Get authoritative match client view
3. POST /api/vault/match/{id}/configure - Configure selected role & stats
4. POST /api/vault/match/{id}/start   - Start battle (advance from SETUP to ACTIVE)
5. GET  /api/vault/match/{id}/state   - Get current battle state (alias)
6. POST /api/vault/match/{id}/turn    - Submit exploit prompt & execute turn
7. GET  /api/vault/match/{id}/turns   - Get turn history
8. GET  /api/vault/match/{id}/result  - Get authoritative match result & settlement

All authoritative logic is controlled by VaultBattleEngine.
Client views are presentation-safe; raw internal prompts are never exposed.
"""

import asyncio
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.game.vault_models import (
    MAX_VAULT_TURNS,
    DEFAULT_VAULT_ENTRY_FEE,
    DEFAULT_VAULT_POT_AMOUNT,
    VaultRole,
    VaultBattleStatus,
    VaultState,
    VaultOutcome,
    VaultResolutionReason,
    WardenConfig,
    AttackerConfig,
    VaultTurn,
    VaultMatchResult,
    VaultMatch,
    VaultMatchClientView,
)
from backend.app.game.vault_stats import (
    VaultStatError,
    build_attacker_agent_profile,
    build_warden_agent_profile,
)
from backend.app.game.vault_engine import (
    VaultBattleEngine,
    get_vault_engine,
    VaultEngineError,
    VaultMatchNotFoundError,
    VaultInvalidStateError,
    VaultMatchResolvedError,
    VaultTurnLimitExceededError,
    VaultInvalidActionError,
)
from backend.app.db.vault_repo import VaultRepository, default_vault_repo
from backend.app.blockchain import get_blockchain_service
from backend.app.game.vault_broadcaster import (
    VaultSSEEventType,
    VaultSSEEvent,
    get_vault_broadcaster,
)

router = APIRouter(prefix="/vault", tags=["vault"])


# ============================================================================
# Request Schemas
# ============================================================================

class CreateVaultMatchRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Player wallet address or identifier")
    player_role: VaultRole = Field(VaultRole.ATTACKER, description="Selected player role (ATTACKER or WARDEN)")
    entry_fee: Decimal = Field(DEFAULT_VAULT_ENTRY_FEE, ge=0, description="Entry fee in MON")
    pot_amount: Decimal = Field(DEFAULT_VAULT_POT_AMOUNT, ge=0, description="Treasury pot in MON")
    attacker_stats: Optional[Dict[str, int]] = Field(None, description="Raw stat allocation for Attacker")
    warden_stats: Optional[Dict[str, int]] = Field(None, description="Raw stat allocation for Warden")


class ConfigureVaultMatchRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Player claiming configuration update")
    selected_role: Optional[VaultRole] = Field(None, description="Updated role selection")
    attacker_stats: Optional[Dict[str, int]] = Field(None, description="Updated Attacker stat allocation")
    warden_stats: Optional[Dict[str, int]] = Field(None, description="Updated Warden stat allocation")


class StartVaultMatchRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Player ID confirming match start")


class SubmitVaultTurnRequest(BaseModel):
    player_id: str = Field(..., min_length=1, description="Player ID submitting the exploit prompt")
    prompt: str = Field(..., min_length=1, description="Exploit transmission prompt")


# ============================================================================
# Helper Functions
# ============================================================================

def resolve_player_id(x_player_id: Optional[str], body_player_id: Optional[str]) -> str:
    """Extract and validate player identity from header or body."""
    resolved = x_player_id or body_player_id
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player identity required via X-Player-ID header or request body.",
        )
    return resolved


async def get_or_restore_match(match_id: str) -> VaultMatch:
    """
    Retrieve authoritative match from engine memory or re-hydrate from PostgreSQL repository.
    Enables state recovery after server restart or container recycling.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    try:
        return engine.get_match(match_id)
    except VaultMatchNotFoundError:
        match = await repo.get_match(match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vault match '{match_id}' not found.",
            )
        # Re-hydrate active in-memory store so subsequent engine methods function
        engine.store.save(match)
        return match


def validate_player_ownership(match: VaultMatch, player_id: str) -> None:
    """Verify that the requesting player owns the match."""
    if match.player_id.lower() != player_id.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Player '{player_id}' is not authorized to act on match '{match.id}'.",
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/match", response_model=VaultMatchClientView, status_code=status.HTTP_201_CREATED)
async def create_vault_match(req: CreateVaultMatchRequest):
    """
    Create a new Vault match in SETUP state.
    Validates initial stat allocations and records initial chamber telemetry.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    try:
        match = engine.create_match(
            player_id=req.player_id,
            player_role=req.player_role,
            entry_fee=req.entry_fee,
            pot_amount=req.pot_amount,
            attacker_stats=req.attacker_stats,
            warden_stats=req.warden_stats,
        )
        await repo.save_match(match)
        return match.to_client_view()
    except VaultStatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create match: {e}")


@router.get("/match/{match_id}", response_model=VaultMatchClientView)
async def get_vault_match(
    match_id: str,
    x_player_id: Optional[str] = Header(None, alias="X-Player-ID"),
    player_id: Optional[str] = Query(None, description="Optional player ID for state query"),
):
    """
    Get authoritative Vault match client view.
    Safe for frequent polling and browser refresh / reconnect recovery.
    """
    match = await get_or_restore_match(match_id)
    return match.to_client_view()


@router.post("/match/{match_id}/configure", response_model=VaultMatchClientView)
async def configure_vault_match(match_id: str, req: ConfigureVaultMatchRequest):
    """
    Configure or update selected role and stat allocation before battle starts.
    Only permitted while match is in SETUP status.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    match = await get_or_restore_match(match_id)
    validate_player_ownership(match, req.player_id)

    if match.status != VaultBattleStatus.SETUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Match '{match_id}' is in state '{match.status}'. Configuration is only allowed in SETUP.",
        )

    try:
        if req.selected_role is not None:
            match.player_role = req.selected_role

        if req.attacker_stats:
            profile = build_attacker_agent_profile(req.attacker_stats)
            match.attacker_config = AttackerConfig(
                name="CHALLENGER STRIKE",
                exploit_power=profile.exploit_power,
                attack_vector_budget=MAX_VAULT_TURNS,
                raw_stats=profile.raw_allocation,
                normalized_stats=profile.normalized_stats,
            )

        if req.warden_stats:
            w_profile = build_warden_agent_profile(req.warden_stats)
            match.warden_config = WardenConfig(
                name="SENTINEL-9",
                security_level=w_profile.security_tier,
                raw_stats=w_profile.raw_allocation,
                normalized_stats=w_profile.normalized_stats,
                system_directive=w_profile.defense_directive,
            )

        engine.store.save(match)
        await repo.save_match(match)
        return match.to_client_view()
    except VaultStatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/match/{match_id}/start", response_model=VaultMatchClientView)
async def start_vault_battle(match_id: str, req: StartVaultMatchRequest):
    """
    Start the Vault intrusion battle.
    Transitions status from SETUP to ACTIVE / ATTACKER_TURN.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    match = await get_or_restore_match(match_id)
    validate_player_ownership(match, req.player_id)

    try:
        updated = engine.start_battle(match_id)
        await repo.save_match(updated)
        return updated.to_client_view()
    except VaultMatchResolvedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except VaultInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/match/{match_id}/state", response_model=VaultMatchClientView)
async def get_vault_battle_state(
    match_id: str,
    x_player_id: Optional[str] = Header(None, alias="X-Player-ID"),
    player_id: Optional[str] = Query(None),
):
    """Alias for GET /api/vault/match/{id} to retrieve current battle telemetry."""
    return await get_vault_match(match_id=match_id, x_player_id=x_player_id, player_id=player_id)


@router.post("/match/{match_id}/turn", response_model=VaultMatchClientView)
async def execute_vault_turn(match_id: str, req: SubmitVaultTurnRequest):
    """
    Submit an exploit prompt and execute an intrusion turn:
    1. Validates match exists, player ownership, and alive state.
    2. Passes prompt to Sentinel-9 agent via AgentProvider.
    3. Authoritatively advances turn counter (1 to 8).
    4. Deterministically evaluates core outcome rules.
    5. Persists turn and state.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    match = await get_or_restore_match(match_id)
    validate_player_ownership(match, req.player_id)

    if match.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Match '{match_id}' is already resolved ({match.status}). No further turns allowed.",
        )

    if match.status not in (VaultBattleStatus.ACTIVE, VaultBattleStatus.ATTACKER_TURN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Match '{match_id}' is in state '{match.status}'. Cannot execute turn.",
        )

    try:
        updated_match = await engine.execute_turn(
            match_id=match_id,
            player_prompt=req.prompt,
            speaker_role=VaultRole.ATTACKER,
        )

        # If match resolved with Attacker breach, populate local mock settlement transaction
        if updated_match.result and updated_match.result.outcome == VaultOutcome.ATTACKER_WINS:
            bc = get_blockchain_service()
            tx_data = await bc.submit_transaction(
                tx_type="VAULT_BREACH_PAYOUT",
                user_id=updated_match.player_id,
                amount=float(updated_match.result.payout_amount),
            )
            updated_match.result.tx_hash = tx_data.get("tx_hash")

        await repo.save_match(updated_match)
        return updated_match.to_client_view()
    except VaultMatchResolvedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (VaultTurnLimitExceededError, VaultInvalidActionError, VaultInvalidStateError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/match/{match_id}/turns", response_model=List[VaultTurn])
async def get_vault_turn_history(match_id: str):
    """Retrieve the authoritative turn history of a match."""
    match = await get_or_restore_match(match_id)
    return match.turns


@router.get("/match/{match_id}/result", response_model=VaultMatchResult)
async def get_vault_match_result(match_id: str):
    """
    Get authoritative final resolution and mock settlement outcome.
    Rejects with 400 if match is still in progress.
    """
    match = await get_or_restore_match(match_id)

    if not match.result or not match.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Match '{match_id}' is not yet resolved. Current status: '{match.status}'.",
        )

    return match.result


@router.get("/match/{match_id}/stream")
@router.get("/match/{match_id}/events")
async def stream_vault_events(
    match_id: str,
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """
    Server-Sent Events (SSE) stream for live Vault battle updates.
    
    Flow:
    1. Verifies match existence in authoritative engine / persistent repo.
    2. Subscribes client queue to VaultEventBroadcaster.
    3. Yields initial 'snapshot' event representing current authoritative server state.
    4. If match is terminal, yields final result and closes stream with [DONE].
    5. Streams real-time events (battle_started, turn_started, agent_thinking,
       agent_dialogue, vault_state_changed, release_event, turn_completed, battle_resolved).
    6. Ensures graceful cleanup on disconnect.
    """
    engine = get_vault_engine()
    repo = default_vault_repo
    broadcaster = engine.broadcaster

    match = await get_or_restore_match(match_id)

    async def sse_generator():
        queue = await broadcaster.subscribe(match_id)
        try:
            # 1. Authoritative snapshot for client sync & reconnect recovery
            current_match = await get_or_restore_match(match_id)
            snapshot_event = VaultSSEEvent(
                id=f"{match_id}_snapshot",
                event=VaultSSEEventType.SNAPSHOT,
                match_id=match_id,
                turn=current_match.current_turn,
                data={
                    "status": current_match.status.value,
                    "vault_state": current_match.vault_state.value,
                    "max_turns": current_match.max_turns,
                    "pot_amount": str(current_match.pot_amount),
                    "player_role": current_match.player_role.value,
                    "is_terminal": current_match.is_terminal,
                    "current_turn": current_match.current_turn,
                    "match": current_match.to_client_view().model_dump(mode="json"),
                },
            )
            yield snapshot_event.to_sse_wire()

            # 2. If match is already terminal, emit final resolution and terminate stream
            if current_match.is_terminal:
                if current_match.result:
                    resolved_event = VaultSSEEvent(
                        id=f"{match_id}_resolved",
                        event=VaultSSEEventType.BATTLE_RESOLVED,
                        match_id=match_id,
                        turn=current_match.current_turn,
                        data={
                            "outcome": current_match.result.outcome.value,
                            "winner_role": current_match.result.winner_role.value,
                            "reason": current_match.result.reason.value,
                            "payout": str(current_match.result.payout_amount),
                            "payout_recipient": current_match.result.payout_recipient,
                            "final_vault_state": current_match.result.final_vault_state.value,
                        },
                    )
                    yield resolved_event.to_sse_wire()
                yield "data: [DONE]\n\n"
                return

            # 3. Stream real-time events from broadcaster
            while True:
                try:
                    msg = await queue.get()
                    yield msg
                    if msg.strip() == "data: [DONE]":
                        break
                except asyncio.CancelledError:
                    break
        finally:
            # 4. Clean up listener registration on exit/disconnect
            await broadcaster.unsubscribe(match_id, queue)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
