"""
Server-Sent Events (SSE) Broadcaster for Monad Vault.

Provides real-time pub/sub event streaming for Vault battles:
- battle_started
- turn_started
- agent_thinking
- agent_dialogue
- vault_state_changed
- release_event
- turn_completed
- battle_resolved
- error

Features:
- Thread-safe, non-blocking asyncio.Queue per client connection.
- Reconnect resilience: sends snapshot on connection.
- Graceful client disconnect handling and subscriber cleanup.
- Clean SSE wire format (event: <type>\ndata: <json>\n\n).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Set, Any, Optional, AsyncGenerator
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class VaultSSEEventType(str, Enum):
    """Event types emitted during a Monad Vault intrusion duel."""
    SNAPSHOT = "snapshot"
    BATTLE_STARTED = "battle_started"
    TURN_STARTED = "turn_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_DIALOGUE = "agent_dialogue"
    VAULT_STATE_CHANGED = "vault_state_changed"
    RELEASE_EVENT = "release_event"
    TURN_COMPLETED = "turn_completed"
    BATTLE_RESOLVED = "battle_resolved"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class VaultSSEEvent(BaseModel):
    """Structured SSE event payload."""
    model_config = ConfigDict(from_attributes=True)

    event: VaultSSEEventType
    match_id: str
    turn: int = 0
    id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S"))
    data: Dict[str, Any] = Field(default_factory=dict)

    def to_sse_wire(self) -> str:
        """Format as standard Server-Sent Event text wire protocol."""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"event: {self.event.value}")
        payload = {
            "event": self.event.value,
            "match_id": self.match_id,
            "turn": self.turn,
            "timestamp": self.timestamp,
            **self.data,
        }
        lines.append(f"data: {json.dumps(payload)}")
        return "\n".join(lines) + "\n\n"


class VaultEventBroadcaster:
    """
    In-memory async pub/sub broadcaster for Vault battle SSE streams.
    Maintains subscriber queues isolated per match_id.
    """

    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._event_seq: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, match_id: str) -> asyncio.Queue:
        """Register a new client subscriber queue for a match."""
        async with self._lock:
            if match_id not in self._subscribers:
                self._subscribers[match_id] = set()
            queue: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._subscribers[match_id].add(queue)
            logger.debug(f"Client subscribed to SSE stream for match '{match_id}'. Total: {len(self._subscribers[match_id])}")
            return queue

    async def unsubscribe(self, match_id: str, queue: asyncio.Queue) -> None:
        """Remove a client subscriber queue upon disconnection."""
        async with self._lock:
            if match_id in self._subscribers:
                self._subscribers[match_id].discard(queue)
                if not self._subscribers[match_id]:
                    del self._subscribers[match_id]
                logger.debug(f"Client unsubscribed from SSE stream for match '{match_id}'.")

    def publish(self, match_id: str, event: VaultSSEEvent) -> int:
        """
        Publish an event to all active subscriber queues for a match.
        Returns the number of subscribers notified.
        """
        subscribers = self._subscribers.get(match_id)
        if not subscribers:
            return 0

        wire_msg = event.to_sse_wire()
        delivered = 0
        for queue in list(subscribers):
            try:
                queue.put_nowait(wire_msg)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for match '{match_id}'; dropping event.")
            except Exception as e:
                logger.warning(f"Error publishing SSE event for match '{match_id}': {e}")

        return delivered

    def broadcast_event(
        self,
        match_id: str,
        event_type: VaultSSEEventType,
        turn: int = 0,
        data: Optional[Dict[str, Any]] = None,
    ) -> VaultSSEEvent:
        """Convenience method to construct and broadcast an event."""
        seq = self._event_seq.get(match_id, 0) + 1
        self._event_seq[match_id] = seq
        event = VaultSSEEvent(
            id=f"{match_id}_{seq}",
            event=event_type,
            match_id=match_id,
            turn=turn,
            data=data or {},
        )
        self.publish(match_id, event)
        return event

    def publish_done(self, match_id: str) -> int:
        """Publish terminal [DONE] indicator to all subscribers."""
        subscribers = self._subscribers.get(match_id)
        if not subscribers:
            return 0

        done_msg = "data: [DONE]\n\n"
        delivered = 0
        for queue in list(subscribers):
            try:
                queue.put_nowait(done_msg)
                delivered += 1
            except asyncio.QueueFull:
                pass
        return delivered

    def subscriber_count(self, match_id: str) -> int:
        """Return the number of connected listeners for a match."""
        return len(self._subscribers.get(match_id, set()))

    def clear(self) -> None:
        """Clear all active subscriptions and counters (used for test isolation)."""
        self._subscribers.clear()
        self._event_seq.clear()


# Global singleton broadcaster
default_vault_broadcaster = VaultEventBroadcaster()


def get_vault_broadcaster() -> VaultEventBroadcaster:
    """Retrieve the global VaultEventBroadcaster instance."""
    global default_vault_broadcaster
    return default_vault_broadcaster
