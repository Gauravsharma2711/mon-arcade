"""
Authoritative Database Persistence Repository for Monad Vault.

Persists full server-owned Vault battle state:
- Match ID, player/challenger ID, role, entry fee, pot amount, currency
- Warden configuration & Attacker configuration (JSON payloads)
- Authoritative lifecycle status and physical vault state (LOCKED/BREACHED)
- Current turn counter (0 to 8) and maximum turn cap (8)
- Turn history (attacker prompts, warden responses, decisions, release calls)
- Dialogue and broadcast event stream
- Authoritative outcome, reason, payout, and timestamps

Reconstruction Guarantee:
- Server can fully reconstruct match state after browser refresh, reconnect, or retry.
- Frontend is never the source of truth.
- Internal AI prompts and secret directives are not exposed in public views.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union

from backend.app.config import settings
from backend.app.db.database import get_db_pool
from backend.app.game.vault_models import (
    MAX_VAULT_TURNS,
    VaultRole,
    VaultBattleStatus,
    VaultState,
    WardenDecision,
    VaultOutcome,
    VaultResolutionReason,
    WardenConfig,
    AttackerConfig,
    VaultDialogueEvent,
    VaultTurn,
    VaultMatchResult,
    VaultMatch,
    VaultMatchClientView,
)
from backend.app.game.vault_engine import default_vault_store, VaultMatchStore

logger = logging.getLogger(__name__)


def parse_dt(val: Any) -> Optional[datetime]:
    """Parse datetime from asyncpg datetime object or ISO string."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return None
    return None


class VaultRepository:
    """
    Authoritative persistence repository for Monad Vault matches and turns.
    Uses asyncpg for PostgreSQL when connected, with seamless in-memory fallback.
    """

    def __init__(self, in_memory_store: Optional[VaultMatchStore] = None):
        self._local_store = in_memory_store if in_memory_store is not None else VaultMatchStore()

    @staticmethod
    def _serialize_json(data: Optional[Any]) -> Optional[str]:
        if data is None:
            return None
        if hasattr(data, "model_dump_json"):
            return data.model_dump_json()
        return json.dumps(data)

    @staticmethod
    def _deserialize_json(payload: Optional[Union[str, dict, list]]) -> Optional[Any]:
        if payload is None:
            return None
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except Exception:
                return None
        return payload

    @classmethod
    def row_to_turn(cls, row: Dict[str, Any]) -> VaultTurn:
        """Convert a database record into a VaultTurn domain entity."""
        decision_raw = row.get("agent_decision") or "DENY_ACCESS"
        try:
            decision = WardenDecision(decision_raw)
        except ValueError:
            decision = WardenDecision.DENY_ACCESS

        return VaultTurn(
            id=row["id"],
            turn_number=row["turn_number"],
            attacker_prompt=row.get("attacker_prompt", ""),
            warden_response=row.get("warden_response", ""),
            warden_decision=decision,
            release_called=bool(row.get("breach_triggered", False)),
            timestamp=parse_dt(row.get("created_at")) or datetime.now(timezone.utc),
        )

    @classmethod
    def row_to_match(cls, row: Dict[str, Any], turns: Optional[List[VaultTurn]] = None) -> VaultMatch:
        """Convert a database record into an authoritative VaultMatch domain entity."""
        # Deserializations
        warden_cfg_data = cls._deserialize_json(row.get("warden_config_payload"))
        warden_cfg = WardenConfig(**warden_cfg_data) if warden_cfg_data else WardenConfig(model=row.get("warden_model", "mock-warden"))

        attacker_cfg_data = cls._deserialize_json(row.get("attacker_config_payload"))
        attacker_cfg = AttackerConfig(**attacker_cfg_data) if attacker_cfg_data else AttackerConfig()

        events_data = cls._deserialize_json(row.get("events_payload")) or []
        events: List[VaultDialogueEvent] = []
        for ev in events_data:
            if isinstance(ev, dict):
                events.append(VaultDialogueEvent(**ev))

        result_data = cls._deserialize_json(row.get("result_payload"))
        result = VaultMatchResult(**result_data) if result_data else None

        role_raw = row.get("player_role") or "ATTACKER"
        status_raw = row.get("status") or "SETUP"
        vault_state_raw = row.get("vault_state") or "LOCKED"

        match = VaultMatch(
            id=row["id"],
            player_id=row.get("challenger_id", "player_1"),
            player_role=VaultRole(role_raw) if role_raw in VaultRole._value2member_map_ else VaultRole.ATTACKER,
            warden_config=warden_cfg,
            attacker_config=attacker_cfg,
            entry_fee=Decimal(str(row.get("entry_fee", 2.5))),
            pot_amount=Decimal(str(row.get("pot_amount", 250.0))),
            currency=row.get("currency", "MON"),
            current_turn=row.get("current_turn", 0),
            max_turns=row.get("turns_allowed", MAX_VAULT_TURNS),
            status=VaultBattleStatus(status_raw) if status_raw in VaultBattleStatus._value2member_map_ else VaultBattleStatus.SETUP,
            vault_state=VaultState(vault_state_raw) if vault_state_raw in VaultState._value2member_map_ else VaultState.LOCKED,
            turns=turns or [],
            events=events,
            result=result,
            created_at=parse_dt(row.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_dt(row.get("updated_at")) or datetime.now(timezone.utc),
            resolved_at=parse_dt(row.get("resolved_at")),
        )
        return match

    async def save_match(self, match: VaultMatch) -> bool:
        """
        Persist full authoritative match state and turns to PostgreSQL via asyncpg.
        Always updates local store as cache / fallback.
        """
        self._local_store.save(match)

        pool = get_db_pool()
        if not pool:
            logger.debug(f"DB pool unavailable; match '{match.id}' kept in memory store.")
            return False

        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # 1. Ensure user exists for foreign key
                    user_id = match.player_id
                    if user_id.startswith("0x") and len(user_id) >= 10:
                        wallet_addr = user_id[:42]
                    else:
                        wallet_addr = f"0x{user_id[:38].ljust(40, '0')}"

                    await conn.execute(
                        """
                        INSERT INTO users (id, wallet_address, created_at, updated_at)
                        VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        user_id,
                        wallet_addr,
                    )

                    # 2. Serialize payloads
                    warden_json = self._serialize_json(match.warden_config)
                    attacker_json = self._serialize_json(match.attacker_config)
                    events_json = json.dumps([ev.model_dump() for ev in match.events])
                    result_json = self._serialize_json(match.result)

                    # 3. Upsert into vault_matches
                    upsert_sql = """
                    INSERT INTO vault_matches (
                        id,
                        challenger_id,
                        warden_model,
                        entry_fee,
                        pot_amount,
                        turns_allowed,
                        status,
                        player_role,
                        current_turn,
                        currency,
                        vault_state,
                        warden_config_payload,
                        attacker_config_payload,
                        events_payload,
                        result_payload,
                        created_at,
                        updated_at,
                        resolved_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                        $12::jsonb, $13::jsonb, $14::jsonb, $15::jsonb,
                        $16, $17, $18
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        current_turn = EXCLUDED.current_turn,
                        vault_state = EXCLUDED.vault_state,
                        events_payload = EXCLUDED.events_payload,
                        result_payload = EXCLUDED.result_payload,
                        updated_at = CURRENT_TIMESTAMP,
                        resolved_at = EXCLUDED.resolved_at;
                    """

                    await conn.execute(
                        upsert_sql,
                        match.id,
                        user_id,
                        match.warden_config.model,
                        match.entry_fee,
                        match.pot_amount,
                        match.max_turns,
                        match.status.value,
                        match.player_role.value,
                        match.current_turn,
                        match.currency,
                        match.vault_state.value,
                        warden_json,
                        attacker_json,
                        events_json,
                        result_json,
                        match.created_at,
                        match.updated_at,
                        match.resolved_at,
                    )

                    # 4. Upsert turn records
                    for turn in match.turns:
                        await conn.execute(
                            """
                            INSERT INTO vault_turns (
                                id,
                                match_id,
                                turn_number,
                                attacker_prompt,
                                warden_response,
                                breach_triggered,
                                acting_role,
                                agent_decision,
                                dialogue_data,
                                resulting_state,
                                created_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (id) DO UPDATE SET
                                warden_response = EXCLUDED.warden_response,
                                breach_triggered = EXCLUDED.breach_triggered,
                                agent_decision = EXCLUDED.agent_decision,
                                resulting_state = EXCLUDED.resulting_state;
                            """,
                            turn.id,
                            match.id,
                            turn.turn_number,
                            turn.attacker_prompt,
                            turn.warden_response,
                            turn.release_called,
                            VaultRole.ATTACKER.value,
                            turn.warden_decision.value,
                            turn.warden_response,
                            match.status.value,
                            turn.timestamp,
                        )

            logger.info(f"Successfully persisted vault match '{match.id}' with {len(match.turns)} turns.")
            return True
        except Exception as e:
            logger.error(f"Failed to persist vault match '{match.id}' to PostgreSQL: {e}", exc_info=True)
            return False

    async def get_match(self, match_id: str) -> Optional[VaultMatch]:
        """
        Retrieve authoritative VaultMatch from PostgreSQL if available,
        falling back to local memory store.
        """
        pool = get_db_pool()
        if not pool:
            return self._local_store.get(match_id)

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM vault_matches WHERE id = $1;",
                    match_id,
                )
                if not row:
                    return self._local_store.get(match_id)

                # Fetch turns
                turn_rows = await conn.fetch(
                    "SELECT * FROM vault_turns WHERE match_id = $1 ORDER BY turn_number ASC;",
                    match_id,
                )
                turns = [self.row_to_turn(dict(tr)) for tr in turn_rows]

                match = self.row_to_match(dict(row), turns=turns)
                self._local_store.save(match)
                return match
        except Exception as e:
            logger.warning(f"Failed to fetch vault match '{match_id}' from DB ({e}); using local fallback.")
            return self._local_store.get(match_id)

    async def list_matches(self, limit: int = 50) -> List[VaultMatch]:
        """List active or recent matches from DB or memory."""
        pool = get_db_pool()
        if not pool:
            return self._local_store.list_matches()[:limit]

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM vault_matches ORDER BY created_at DESC LIMIT $1;",
                    limit,
                )
                matches = []
                for row in rows:
                    turn_rows = await conn.fetch(
                        "SELECT * FROM vault_turns WHERE match_id = $1 ORDER BY turn_number ASC;",
                        row["id"],
                    )
                    turns = [self.row_to_turn(dict(tr)) for tr in turn_rows]
                    matches.append(self.row_to_match(dict(row), turns=turns))
                return matches
        except Exception as e:
            logger.warning(f"Failed to list vault matches from DB ({e}); using local fallback.")
            return self._local_store.list_matches()[:limit]


# Default singleton instance
default_vault_repo = VaultRepository()
