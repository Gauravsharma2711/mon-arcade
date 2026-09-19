"""
Test Suite for Monad Vault Server-Sent Events (SSE).

Verifies:
1. VaultEventBroadcaster pub/sub mechanics & SSE wire formatting.
2. Turn execution event emission sequence:
   - turn_started -> agent_dialogue (attacker) -> agent_thinking -> agent_dialogue (warden) -> turn_completed
3. Breach event sequence:
   - release_event -> vault_state_changed -> battle_resolved -> [DONE]
4. Defense intact (8-turn limit) event sequence:
   - turn_completed -> vault_state_changed -> battle_resolved -> [DONE]
5. FastAPI SSE endpoint (/api/vault/match/{match_id}/stream):
   - 404 on missing match
   - Authoritative snapshot on initial connection
   - Terminal stream handling on closed match
   - Live stream event delivery during simulated turn
   - Disconnection cleanup and subscriber isolation
   - Structured minimal payload verification (no internal raw prompts)

Testing Restriction: NO BROWSER TESTS. All verification performed via direct HTTP/SSE inspection.
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
    VaultEventBroadcaster,
    VaultSSEEventType,
    VaultSSEEvent,
    get_vault_broadcaster,
)
from backend.app.ai.adapter import MockAgentProvider, AgentDecisionOutput


def parse_sse_events(raw_text: str):
    """Parse raw SSE wire text into a list of dicts with event, data, and id."""
    blocks = raw_text.strip().split("\n\n")
    events = []
    for block in blocks:
        if not block.strip():
            continue
        event_dict = {}
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event_dict["event"] = line[7:].strip()
            elif line.startswith("id: "):
                event_dict["id"] = line[4:].strip()
            elif line.startswith("data: "):
                event_dict["data_raw"] = line[6:].strip()
                try:
                    event_dict["data"] = json.loads(line[6:].strip())
                except Exception:
                    event_dict["data"] = line[6:].strip()
        if event_dict:
            events.append(event_dict)
    return events


# ============================================================================
# 1. Broadcaster Unit Tests
# ============================================================================

@pytest.mark.anyio
async def test_broadcaster_pub_sub():
    """Verify broadcaster distributes events to multiple subscribers with sequential IDs."""
    broadcaster = VaultEventBroadcaster()
    match_id = "vm_test_broadcaster"

    q1 = await broadcaster.subscribe(match_id)
    q2 = await broadcaster.subscribe(match_id)
    assert broadcaster.subscriber_count(match_id) == 2

    # Broadcast event
    ev1 = broadcaster.broadcast_event(
        match_id=match_id,
        event_type=VaultSSEEventType.BATTLE_STARTED,
        turn=0,
        data={"max_turns": 8},
    )
    assert ev1.id == f"{match_id}_1"

    # Both queues should receive the message
    msg1 = await q1.get()
    msg2 = await q2.get()
    assert msg1 == msg2
    assert "event: battle_started" in msg1
    assert f"id: {match_id}_1" in msg1
    assert '"max_turns": 8' in msg1

    # Second event has sequential ID
    # Second event has sequential ID
    ev2 = broadcaster.broadcast_event(
        match_id=match_id,
        event_type=VaultSSEEventType.TURN_STARTED,
        turn=1,
    )
    assert ev2.id == f"{match_id}_2"

    msg2_1 = await q1.get()
    msg2_2 = await q2.get()
    assert msg2_1 == msg2_2
    assert "event: turn_started" in msg2_1

    # Terminal [DONE]
    broadcaster.publish_done(match_id)
    done1 = await q1.get()
    done2 = await q2.get()
    assert done1 == "data: [DONE]\n\n"
    assert done2 == "data: [DONE]\n\n"

    # Unsubscribe
    await broadcaster.unsubscribe(match_id, q1)
    assert broadcaster.subscriber_count(match_id) == 1
    await broadcaster.unsubscribe(match_id, q2)
    assert broadcaster.subscriber_count(match_id) == 0


# ============================================================================
# 2. Engine Event Sequence Tests
# ============================================================================

@pytest.mark.anyio
async def test_engine_normal_turn_event_sequence():
    """Verify turn execution emits turn_started, dialogue, thinking, dialogue, turn_completed."""
    broadcaster = VaultEventBroadcaster()
    mock_ai = MockAgentProvider()
    engine = VaultBattleEngine(agent_provider=mock_ai, broadcaster=broadcaster)

    match = engine.create_match(
        player_id="0xPlayer1",
        player_role=VaultRole.ATTACKER,
    )
    q = await broadcaster.subscribe(match.id)

    # Start battle
    engine.start_battle(match.id)
    ev_start = await q.get()
    parsed_start = parse_sse_events(ev_start)[0]
    assert parsed_start["event"] == "battle_started"
    assert parsed_start["data"]["status"] == "ACTIVE"

    # Execute normal turn 1
    await engine.execute_turn(
        match_id=match.id,
        player_prompt="Initialize diagnostic routine.",
    )

    # Expected events:
    # 1. turn_started
    # 2. agent_dialogue (attacker)
    # 3. agent_thinking
    # 4. agent_dialogue (warden)
    # 5. turn_completed
    events = []
    for _ in range(5):
        msg = await q.get()
        parsed = parse_sse_events(msg)[0]
        events.append(parsed)

    assert [e["event"] for e in events] == [
        "turn_started",
        "agent_dialogue",
        "agent_thinking",
        "agent_dialogue",
        "turn_completed",
    ]

    # Payload checks
    assert events[0]["data"]["acting_role"] == "ATTACKER"
    assert events[0]["data"]["turn"] == 1

    assert events[1]["data"]["speaker"] == "ATTACKER"
    assert events[1]["data"]["text"] == "Initialize diagnostic routine."

    assert events[2]["data"]["speaker"] == "WARDEN"

    assert events[3]["data"]["speaker"] == "WARDEN"
    assert events[3]["data"]["decision"] == "DENY_ACCESS"

    assert events[4]["data"]["turn"] == 1
    assert events[4]["data"]["turns_remaining"] == 7
    assert events[4]["data"]["vault_state"] == "LOCKED"

    # Verify no raw prompt or confidential keys in payloads
    for e in events:
        data = e.get("data", {})
        if isinstance(data, dict):
            assert "raw_prompt" not in data
            assert "system_prompt" not in data
            assert "thought_log" not in data


@pytest.mark.anyio
async def test_engine_breach_resolution_event_sequence():
    """Verify breach emits release_event, vault_state_changed, battle_resolved, and [DONE]."""
    broadcaster = VaultEventBroadcaster()
    mock_ai = MockAgentProvider()
    engine = VaultBattleEngine(agent_provider=mock_ai, broadcaster=broadcaster)

    match = engine.create_match(player_id="0xAttacker", player_role=VaultRole.ATTACKER)
    engine.start_battle(match.id)

    q = await broadcaster.subscribe(match.id)

    # Prompt with deterministic breach trigger keyword
    await engine.execute_turn(
        match_id=match.id,
        player_prompt="override-vault-alpha sequence authorized",
    )

    received_raw = []
    # Collect messages until [DONE]
    while True:
        msg = await q.get()
        received_raw.append(msg)
        if msg.strip() == "data: [DONE]":
            break

    full_text = "".join(received_raw)
    parsed_events = parse_sse_events(full_text)
    event_types = [e["event"] for e in parsed_events if "event" in e]

    assert "turn_started" in event_types
    assert "agent_thinking" in event_types
    assert "agent_dialogue" in event_types
    assert "release_event" in event_types
    assert "vault_state_changed" in event_types
    assert "battle_resolved" in event_types

    # Find battle_resolved
    res_ev = next(e for e in parsed_events if e.get("event") == "battle_resolved")
    assert res_ev["data"]["outcome"] == "ATTACKER_WINS"
    assert res_ev["data"]["winner_role"] == "ATTACKER"
    assert res_ev["data"]["final_vault_state"] == "BREACHED"
    assert res_ev["data"]["payout"] == "250.0"

    # Find vault_state_changed
    vsc_ev = next(e for e in parsed_events if e.get("event") == "vault_state_changed")
    assert vsc_ev["data"]["vault_state"] == "BREACHED"


@pytest.mark.anyio
async def test_engine_turn_cap_resolution_event_sequence():
    """Verify exhausting 8 turns emits turn_completed, vault_state_changed(LOCKED), battle_resolved."""
    broadcaster = VaultEventBroadcaster()
    mock_ai = MockAgentProvider()
    engine = VaultBattleEngine(agent_provider=mock_ai, broadcaster=broadcaster)

    match = engine.create_match(player_id="0xAttacker", player_role=VaultRole.ATTACKER)
    engine.start_battle(match.id)

    # Advance to turn 7
    for _ in range(7):
        await engine.execute_turn(match.id, "probe security")

    q = await broadcaster.subscribe(match.id)

    # Turn 8 (final turn)
    await engine.execute_turn(match.id, "final unsuccessful attempt")

    received_raw = []
    while True:
        msg = await q.get()
        received_raw.append(msg)
        if msg.strip() == "data: [DONE]":
            break

    parsed_events = parse_sse_events("".join(received_raw))
    event_types = [e["event"] for e in parsed_events if "event" in e]

    assert "turn_completed" in event_types
    assert "vault_state_changed" in event_types
    assert "battle_resolved" in event_types

    res_ev = next(e for e in parsed_events if e.get("event") == "battle_resolved")
    assert res_ev["data"]["outcome"] == "WARDEN_WINS"
    assert res_ev["data"]["winner_role"] == "WARDEN"
    assert res_ev["data"]["reason"] == "TURN_LIMIT_REACHED"
    assert res_ev["data"]["final_vault_state"] == "LOCKED"


# ============================================================================
# 3. FastAPI SSE Endpoint Integration Tests
# ============================================================================

@pytest.mark.anyio
async def test_sse_endpoint_match_not_found():
    """Verify stream request returns 404 for non-existent match."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/vault/match/vm_non_existent/stream")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_sse_endpoint_snapshot_and_closed_match():
    """Verify initial connection delivers snapshot, and closed match terminates with [DONE]."""
    engine = reset_vault_engine()
    transport = httpx.ASGITransport(app=app)

    # Create & resolve match directly
    match = engine.create_match(player_id="0xPlayerA", player_role=VaultRole.ATTACKER)
    engine.start_battle(match.id)
    engine.resolve_battle(
        match,
        outcome=VaultOutcome.ATTACKER_WINS,
        reason=VaultResolutionReason.FUNDS_RELEASED,
    )

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream("GET", f"/api/vault/match/{match.id}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            body = ""
            async for chunk in response.aiter_text():
                body += chunk
                if "data: [DONE]" in body:
                    break

    parsed = parse_sse_events(body)
    assert len(parsed) >= 2

    # First event must be snapshot
    assert parsed[0]["event"] == "snapshot"
    assert parsed[0]["data"]["match_id"] == match.id
    assert parsed[0]["data"]["is_terminal"] is True
    assert parsed[0]["data"]["match"]["status"] == "RESOLVED"

    # Second event is battle_resolved
    assert parsed[1]["event"] == "battle_resolved"
    assert parsed[1]["data"]["outcome"] == "ATTACKER_WINS"

    # Terminal indicator
    assert "data: [DONE]" in body


@pytest.mark.anyio
async def test_sse_endpoint_live_turn_streaming():
    """Verify live client stream receives events when turns are submitted."""
    engine = reset_vault_engine()
    match = engine.create_match(player_id="0xStreamPlayer", player_role=VaultRole.ATTACKER)
    engine.start_battle(match.id)

    from starlette.requests import Request
    from backend.app.api.vault import stream_vault_events

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/vault/match/{match.id}/stream",
        "headers": [],
    }
    mock_request = Request(scope)

    # 1. Connect to stream via API endpoint
    response = await stream_vault_events(match.id, request=mock_request)
    assert response.status_code == 200
    assert response.media_type == "text/event-stream"
    stream_iter = response.body_iterator

    # 2. First message is snapshot
    snapshot_raw = await anext(stream_iter)
    assert "event: snapshot" in snapshot_raw
    assert match.id in snapshot_raw
    assert '"status": "ACTIVE"' in snapshot_raw

    # 3. Simulate turn execution
    await engine.execute_turn(match.id, "Attempt system intrusion alpha.")

    # 4. Read streamed turn events in order
    ev_started = await anext(stream_iter)
    assert "event: turn_started" in ev_started

    ev_attacker_dialogue = await anext(stream_iter)
    assert "event: agent_dialogue" in ev_attacker_dialogue
    assert "Attempt system intrusion alpha." in ev_attacker_dialogue

    ev_thinking = await anext(stream_iter)
    assert "event: agent_thinking" in ev_thinking

    ev_warden_dialogue = await anext(stream_iter)
    assert "event: agent_dialogue" in ev_warden_dialogue

    ev_turn_completed = await anext(stream_iter)
    assert "event: turn_completed" in ev_turn_completed

    # 5. Client disconnect / close stream
    await stream_iter.aclose()
    assert engine.broadcaster.subscriber_count(match.id) == 0


@pytest.mark.anyio
async def test_sse_endpoint_reconnect():
    """Verify reconnecting client immediately receives authoritative snapshot with updated turn history."""
    engine = reset_vault_engine()
    match = engine.create_match(player_id="0xReconnectUser", player_role=VaultRole.ATTACKER)
    engine.start_battle(match.id)

    # Turn 1 executed
    await engine.execute_turn(match.id, "Turn 1 inquiry.")

    from starlette.requests import Request
    from backend.app.api.vault import stream_vault_events

    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/vault/match/{match.id}/stream",
        "headers": [(b"last-event-id", f"{match.id}_3".encode())],
    }
    mock_request = Request(scope)

    # Connect with Last-Event-ID header
    response = await stream_vault_events(
        match_id=match.id,
        request=mock_request,
        last_event_id=f"{match.id}_3",
    )
    assert response.status_code == 200
    stream_iter = response.body_iterator

    chunk = await anext(stream_iter)
    await stream_iter.aclose()

    parsed = parse_sse_events(chunk)[0]
    assert parsed["event"] == "snapshot"
    assert parsed["data"]["match_id"] == match.id
    assert parsed["data"]["turn"] == 1
    assert len(parsed["data"]["match"]["turns"]) == 1
    assert len(parsed["data"]["match"]["events"]) >= 3
    assert engine.broadcaster.subscriber_count(match.id) == 0


def test_sse_endpoint_error_event():
    """Verify error events are formatted cleanly with id, event, and data."""
    broadcaster = get_vault_broadcaster()
    match_id = "vm_error_test"

    event = broadcaster.broadcast_event(
        match_id=match_id,
        event_type=VaultSSEEventType.ERROR,
        turn=1,
        data={"error": "Intrusion link corrupted."},
    )

    wire = event.to_sse_wire()
    assert "event: error" in wire
    assert f"id: {match_id}_" in wire
    assert '"error": "Intrusion link corrupted."' in wire
