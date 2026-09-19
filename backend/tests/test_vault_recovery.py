"""
Test Suite for Monad Vault Recovery and Reconnect Mechanics.

Verifies:
1. Server restart recovery: In-memory engine store clear simulates server restart;
   requests to /api/vault/match/{id}, /turns, and /turn re-hydrate from persistent repository.
2. Client reconnect to SSE stream receives authoritative snapshot of current turn and state.
3. Reconnect to an already-resolved match returns terminal snapshot and [DONE].
4. Client disconnect & re-subscription: Clean unsubscription on drop and re-subscription without state corruption.
5. Deduplication of SSE events: Broadcast IDs are unique and monotonic per match.
6. Turn failure resilience: Failed/invalid turn request preserves match state for retry.

Testing Restriction: NO BROWSER TESTS. All verification via direct API & engine tests.
"""

import asyncio
import json
import pytest
from decimal import Decimal
import httpx

from backend.app.main import app
from backend.app.game.vault_models import (
    VaultRole,
    VaultBattleStatus,
    VaultState,
    VaultOutcome,
    VaultResolutionReason,
    WardenDecision,
    AttackerConfig,
    WardenConfig,
)
from backend.app.game.vault_engine import (
    VaultBattleEngine,
    reset_vault_engine,
    get_vault_engine,
)
from backend.app.game.vault_broadcaster import (
    VaultSSEEventType,
    VaultSSEEvent,
)
from backend.app.ai.adapter import MockAgentProvider, AgentDecisionOutput
from backend.app.api.vault import default_vault_repo


def parse_sse_events(raw_text: str):
    """Parse raw SSE wire text into a list of dicts with event, data, and id."""
    blocks = raw_text.strip().split("\n\n")
    events = []
    for block in blocks:
        if not block.strip():
            continue
        event_type = None
        event_id = None
        event_data = None
        for line in block.split("\n"):
            if line.startswith("id: "):
                event_id = line[4:].strip()
            elif line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                raw_data = line[6:].strip()
                try:
                    event_data = json.loads(raw_data)
                except Exception:
                    event_data = raw_data
        if event_type or event_data:
            events.append({"id": event_id, "event": event_type, "data": event_data})
    return events


@pytest.fixture(autouse=True)
def clean_vault_state():
    """Reset the engine before each test."""
    reset_vault_engine()
    yield
    reset_vault_engine()


@pytest.mark.anyio
async def test_recovery_from_persistence_after_engine_cache_clear():
    """
    Test server restart recovery:
    Clearing engine.store simulates a cold server restart.
    Verifies that get_or_restore_match re-hydrates match and turns from repository.
    """
    engine = get_vault_engine()
    repo = default_vault_repo

    # 1. Create a match and start battle
    match = engine.create_match(
        player_id="recov_player_1",
        player_role=VaultRole.ATTACKER,
        entry_fee=Decimal("2.5"),
        pot_amount=Decimal("250.0"),
    )
    engine.start_battle(match.id)

    # 2. Execute turn 1
    await engine.execute_turn(
        match_id=match.id,
        player_prompt="Initialize handshake protocol.",
        speaker_role=VaultRole.ATTACKER,
    )
    await repo.save_match(match)

    # 3. Simulate cold server restart by wiping the engine's in-memory store
    engine.store.clear()
    assert engine.store.get(match.id) is None

    # 4. Verify API requests re-hydrate the match transparently
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # GET /match/{id}
        resp = await client.get(f"/api/vault/match/{match.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == match.id
        assert data["current_turn"] == 1
        assert data["status"] in ("ACTIVE", "ATTACKER_TURN")

        # In-memory store should now be re-hydrated
        assert engine.store.get(match.id) is not None

        # GET /match/{id}/turns
        turns_resp = await client.get(f"/api/vault/match/{match.id}/turns")
        assert turns_resp.status_code == 200
        turns_data = turns_resp.json()
        assert len(turns_data) == 1
        assert turns_data[0]["attacker_prompt"] == "Initialize handshake protocol."

        # POST /match/{id}/turn (Turn 2 succeeds after server recovery)
        turn2_resp = await client.post(
            f"/api/vault/match/{match.id}/turn",
            json={"player_id": "recov_player_1", "prompt": "Provide security clearance credentials."},
        )
        assert turn2_resp.status_code == 200
        turn2_data = turn2_resp.json()
        assert turn2_data["current_turn"] == 2


@pytest.mark.anyio
async def test_reconnect_sse_receives_current_authoritative_snapshot():
    """
    Test reconnecting client to SSE stream:
    Verifies that when a client drops and reconnects mid-battle,
    the initial event is an authoritative snapshot representing current turn and pot.
    """
    engine = get_vault_engine()
    match = engine.create_match(
        player_id="recov_player_2",
        player_role=VaultRole.ATTACKER,
        pot_amount=Decimal("500.0"),
    )
    engine.start_battle(match.id)

    # Advance to turn 3
    for i in range(1, 4):
        await engine.execute_turn(
            match_id=match.id,
            player_prompt=f"Exploit attempt #{i}",
            speaker_role=VaultRole.ATTACKER,
        )

    # Reconnect to SSE stream directly via endpoint
    from starlette.requests import Request
    from backend.app.api.vault import stream_vault_events

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/vault/match/{match.id}/stream",
        "headers": [],
    }
    mock_request = Request(scope)
    response = await stream_vault_events(match.id, request=mock_request)
    assert response.status_code == 200
    stream_iter = response.body_iterator

    first_chunk = await anext(stream_iter)
    await stream_iter.aclose()

    events = parse_sse_events(first_chunk)
    assert len(events) >= 1
    snapshot = events[0]
    assert snapshot["event"] == "snapshot"
    assert snapshot["data"]["current_turn"] == 3
    assert snapshot["data"]["max_turns"] == 8
    assert Decimal(snapshot["data"]["pot_amount"]) == Decimal("500.0")
    assert snapshot["data"]["is_terminal"] is False


@pytest.mark.anyio
async def test_reconnect_to_already_resolved_match():
    """
    Test reconnect to a match that resolved while client was offline:
    Verifies that client receives terminal snapshot, battle_resolved event, and stream terminates.
    """
    engine = get_vault_engine()
    match = engine.create_match(
        player_id="recov_player_3",
        player_role=VaultRole.ATTACKER,
    )
    engine.start_battle(match.id)
    engine.resolve_battle(
        match,
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
    )
    assert match.is_terminal
    assert match.result.outcome == VaultOutcome.ATTACKER_WINS

    from starlette.requests import Request
    from backend.app.api.vault import stream_vault_events

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/vault/match/{match.id}/stream",
        "headers": [],
    }
    mock_request = Request(scope)
    response = await stream_vault_events(match.id, request=mock_request)
    assert response.status_code == 200
    stream_iter = response.body_iterator

    chunks = []
    async for chunk in stream_iter:
        chunks.append(chunk)
        if "[DONE]" in chunk:
            break

    raw_text = "".join(chunks)
    events = parse_sse_events(raw_text)

    event_types = [e["event"] for e in events]
    assert "snapshot" in event_types
    assert "battle_resolved" in event_types
    assert "[DONE]" in raw_text

    # Verify resolution data inside SSE event
    res_ev = next(e for e in events if e["event"] == "battle_resolved")
    assert res_ev["data"]["outcome"] == "ATTACKER_WINS"
    assert res_ev["data"]["winner_role"] == "ATTACKER"


@pytest.mark.anyio
async def test_duplicate_sse_events_deduplication_contract():
    """
    Verify that broadcaster emits monotonic unique IDs per event,
    enabling deterministic deduplication on client side.
    """
    engine = get_vault_engine()
    match = engine.create_match(player_id="recov_player_4")
    broadcaster = engine.broadcaster

    ev1 = broadcaster.broadcast_event(match.id, VaultSSEEventType.AGENT_THINKING, turn=1, data={"speaker": "WARDEN"})
    ev2 = broadcaster.broadcast_event(match.id, VaultSSEEventType.AGENT_THINKING, turn=1, data={"speaker": "WARDEN"})
    ev3 = broadcaster.broadcast_event(match.id, VaultSSEEventType.TURN_COMPLETED, turn=1, data={"turns_remaining": 7})

    # IDs must be unique and monotonic
    assert ev1.id != ev2.id
    assert ev2.id != ev3.id
    assert ev1.id.endswith("_1")
    assert ev2.id.endswith("_2")
    assert ev3.id.endswith("_3")


@pytest.mark.anyio
async def test_simulated_client_disconnect_and_reconnect():
    """
    Test broadcaster subscriber lifecycle during connection loss:
    Client subscribing, dropping, and reconnecting maintains accurate subscriber counts.
    """
    engine = get_vault_engine()
    broadcaster = engine.broadcaster
    match_id = "test_sub_lifecycle_match"

    # Subscriber 1 connects
    q1 = await broadcaster.subscribe(match_id)
    assert len(broadcaster._subscribers[match_id]) == 1

    # Client 1 drops/unsubscribes
    await broadcaster.unsubscribe(match_id, q1)
    assert match_id not in broadcaster._subscribers or len(broadcaster._subscribers[match_id]) == 0

    # Client reconnects
    q2 = await broadcaster.subscribe(match_id)
    assert len(broadcaster._subscribers[match_id]) == 1

    # Clean up
    await broadcaster.unsubscribe(match_id, q2)


@pytest.mark.anyio
async def test_turn_failure_recovery_preserves_state():
    """
    Test turn failure resilience:
    Submitting an invalid turn (e.g. wrong player) fails with 403,
    preserving the current turn count so legitimate player can retry.
    """
    engine = get_vault_engine()
    match = engine.create_match(
        player_id="legit_player",
        player_role=VaultRole.ATTACKER,
    )
    engine.start_battle(match.id)
    assert match.current_turn == 0

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Unauthorized player attempts turn -> rejected
        fail_resp = await client.post(
            f"/api/vault/match/{match.id}/turn",
            json={"player_id": "impostor_player", "prompt": "Bypass check"},
        )
        assert fail_resp.status_code == 403

        # State remains preserved at turn 0
        state_resp = await client.get(f"/api/vault/match/{match.id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["current_turn"] == 0

        # Legitimate player executes turn -> succeeds and advances to turn 1
        ok_resp = await client.post(
            f"/api/vault/match/{match.id}/turn",
            json={"player_id": "legit_player", "prompt": "Legitimate infiltration query."},
        )
        assert ok_resp.status_code == 200
        assert ok_resp.json()["current_turn"] == 1
