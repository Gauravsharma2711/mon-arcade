"""
Authoritative Database Persistence Repository for Bluff or Bust.

Persists full server-owned match state:
- Match ID, stake amount, pot amount, status, timestamps
- Player IDs (foreign keys to users table, auto-provisioned if needed)
- Creator commitment: secret, salt, hash, action, timing
- Opponent commitment: secret, salt, hash, action, timing
- Timing authority: active turn player, countdown deadline, turn seconds allowed
- Outcome & Showdown: winner ID, resolution reason, payout transaction hash, result payload

Maintains strict state boundary:
- Database holds complete authoritative server state.
- Client state sanitization is performed on read via match.to_client_view().
- Opponent secrets and salts are never leaked prematurely.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union

from backend.app.config import settings
from backend.app.db.database import get_db_pool
from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffResolutionReason,
    BluffSettlementStatus,
    RevealedPlayerValue,
    BluffMatchResult,
    PlayerCommitment,
    BluffMatch,
)

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


class BluffRepository:
    """
    Authoritative persistence repository for Bluff or Bust matches.
    Uses asyncpg for PostgreSQL when connected, with graceful fallback.
    """

    @staticmethod
    def _serialize_result_payload(result: Optional[BluffMatchResult]) -> Optional[str]:
        if not result:
            return None
        return result.model_dump_json()

    @staticmethod
    def _deserialize_result_payload(payload: Optional[Union[str, dict]]) -> Optional[BluffMatchResult]:
        if not payload:
            return None
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
        return BluffMatchResult(**data)

    @classmethod
    def row_to_match(cls, row: Dict[str, Any]) -> BluffMatch:
        """Convert a database record into an authoritative BluffMatch domain entity."""
        # Creator commitment
        creator_comm = PlayerCommitment(
            player_id=row["creator_id"],
            secret_value=row.get("creator_secret"),
            salt=row.get("creator_salt"),
            commitment_hash=row.get("creator_commitment_hash"),
            has_committed=bool(row.get("creator_has_committed", False)),
            committed_at=parse_dt(row.get("created_at")),
            action=BluffAction(row["creator_action"]) if row.get("creator_action") else None,
            action_at=parse_dt(row.get("creator_action_at")),
        )

        # Opponent commitment (if joined)
        opponent_comm: Optional[PlayerCommitment] = None
        if row.get("opponent_id"):
            opponent_comm = PlayerCommitment(
                player_id=row["opponent_id"],
                secret_value=row.get("opponent_secret"),
                salt=row.get("opponent_salt"),
                commitment_hash=row.get("opponent_commitment_hash"),
                has_committed=bool(row.get("opponent_has_committed", False)),
                committed_at=parse_dt(row.get("updated_at")),
                action=BluffAction(row["opponent_action"]) if row.get("opponent_action") else None,
                action_at=parse_dt(row.get("opponent_action_at")),
            )

        # Result structure
        result: Optional[BluffMatchResult] = None
        raw_result = row.get("result_payload")
        if raw_result:
            result = cls._deserialize_result_payload(raw_result)

        # Status and reason enums
        status = BluffMatchStatus(row["status"])
        reason = BluffResolutionReason(row["resolution_reason"]) if row.get("resolution_reason") else None

        # Build domain entity
        match = BluffMatch(
            id=row["id"],
            creator_id=row["creator_id"],
            opponent_id=row.get("opponent_id"),
            stake_amount=Decimal(str(row["stake_amount"])),
            pot_amount=Decimal(str(row.get("pot_amount") or (Decimal(str(row["stake_amount"])) * 2))),
            status=status,
            creator_commitment=creator_comm,
            opponent_commitment=opponent_comm,
            active_turn_player_id=row.get("active_turn_player_id"),
            turn_deadline=parse_dt(row.get("turn_deadline")),
            turn_seconds_allowed=row.get("turn_seconds_allowed", 15),
            winner_id=row.get("winner_id"),
            resolution_reason=reason,
            payout_tx_hash=row.get("payout_tx_hash"),
            result=result,
            created_at=parse_dt(row.get("created_at")) or datetime.now(timezone.utc),
            updated_at=parse_dt(row.get("updated_at")) or datetime.now(timezone.utc),
            resolved_at=parse_dt(row.get("resolved_at")),
        )
        return match

    async def save(self, match: BluffMatch) -> bool:
        """
        Persist full authoritative match state to PostgreSQL via asyncpg.
        Returns True if persisted to DB, False if running standalone/unconnected.
        """
        pool = get_db_pool()
        if not pool:
            logger.debug(f"DB pool unavailable; match {match.id} kept in active store.")
            return False

        try:
            async with pool.acquire() as conn:
                # 1. Ensure players exist in users table for FK integrity
                await conn.execute(
                    """
                    INSERT INTO users (id, wallet_address)
                    VALUES ($1, $1)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    match.creator_id,
                )
                if match.opponent_id:
                    await conn.execute(
                        """
                        INSERT INTO users (id, wallet_address)
                        VALUES ($1, $1)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        match.opponent_id,
                    )
                if match.winner_id:
                    await conn.execute(
                        """
                        INSERT INTO users (id, wallet_address)
                        VALUES ($1, $1)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        match.winner_id,
                    )

                # 2. Extract commitment values
                c_secret = match.creator_commitment.secret_value
                c_salt = match.creator_commitment.salt
                c_hash = match.creator_commitment.commitment_hash
                c_committed = match.creator_commitment.has_committed
                c_action = match.creator_commitment.action.value if match.creator_commitment.action else None
                c_action_at = match.creator_commitment.action_at

                o_secret = match.opponent_commitment.secret_value if match.opponent_commitment else None
                o_salt = match.opponent_commitment.salt if match.opponent_commitment else None
                o_hash = match.opponent_commitment.commitment_hash if match.opponent_commitment else None
                o_committed = match.opponent_commitment.has_committed if match.opponent_commitment else False
                o_action = (
                    match.opponent_commitment.action.value
                    if (match.opponent_commitment and match.opponent_commitment.action)
                    else None
                )
                o_action_at = match.opponent_commitment.action_at if match.opponent_commitment else None

                reason = match.resolution_reason.value if match.resolution_reason else None
                result_json = self._serialize_result_payload(match.result)

                # 3. Upsert into bluff_matches
                await conn.execute(
                    """
                    INSERT INTO bluff_matches (
                        id, creator_id, opponent_id, stake_amount, pot_amount,
                        creator_secret, creator_salt, creator_commitment_hash, creator_has_committed,
                        creator_action, creator_action_at,
                        opponent_secret, opponent_salt, opponent_commitment_hash, opponent_has_committed,
                        opponent_action, opponent_action_at,
                        active_turn_player_id, turn_deadline, turn_seconds_allowed,
                        winner_id, status, resolution_reason, payout_tx_hash,
                        result_payload, created_at, updated_at, resolved_at
                    ) VALUES (
                        $1, $2, $3, $4, $5,
                        $6, $7, $8, $9,
                        $10, $11,
                        $12, $13, $14, $15,
                        $16, $17,
                        $18, $19, $20,
                        $21, $22, $23, $24,
                        $25, $26, $27, $28
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        opponent_id = EXCLUDED.opponent_id,
                        stake_amount = EXCLUDED.stake_amount,
                        pot_amount = EXCLUDED.pot_amount,
                        creator_secret = EXCLUDED.creator_secret,
                        creator_salt = EXCLUDED.creator_salt,
                        creator_commitment_hash = EXCLUDED.creator_commitment_hash,
                        creator_has_committed = EXCLUDED.creator_has_committed,
                        creator_action = EXCLUDED.creator_action,
                        creator_action_at = EXCLUDED.creator_action_at,
                        opponent_secret = EXCLUDED.opponent_secret,
                        opponent_salt = EXCLUDED.opponent_salt,
                        opponent_commitment_hash = EXCLUDED.opponent_commitment_hash,
                        opponent_has_committed = EXCLUDED.opponent_has_committed,
                        opponent_action = EXCLUDED.opponent_action,
                        opponent_action_at = EXCLUDED.opponent_action_at,
                        active_turn_player_id = EXCLUDED.active_turn_player_id,
                        turn_deadline = EXCLUDED.turn_deadline,
                        turn_seconds_allowed = EXCLUDED.turn_seconds_allowed,
                        winner_id = EXCLUDED.winner_id,
                        status = EXCLUDED.status,
                        resolution_reason = EXCLUDED.resolution_reason,
                        payout_tx_hash = EXCLUDED.payout_tx_hash,
                        result_payload = EXCLUDED.result_payload,
                        updated_at = EXCLUDED.updated_at,
                        resolved_at = EXCLUDED.resolved_at;
                    """,
                    match.id,
                    match.creator_id,
                    match.opponent_id,
                    match.stake_amount,
                    match.pot_amount,
                    c_secret,
                    c_salt,
                    c_hash,
                    c_committed,
                    c_action,
                    c_action_at,
                    o_secret,
                    o_salt,
                    o_hash,
                    o_committed,
                    o_action,
                    o_action_at,
                    match.active_turn_player_id,
                    match.turn_deadline,
                    match.turn_seconds_allowed,
                    match.winner_id,
                    match.status.value,
                    reason,
                    match.payout_tx_hash,
                    result_json,
                    match.created_at,
                    match.updated_at,
                    match.resolved_at,
                )
                logger.debug(f"Match {match.id} successfully persisted to PostgreSQL.")
                return True
        except Exception as e:
            logger.warning(f"Failed to persist match {match.id} to PostgreSQL: {e}")
            return False

    async def get(self, match_id: str) -> Optional[BluffMatch]:
        """Retrieve and reconstruct authoritative BluffMatch from PostgreSQL."""
        pool = get_db_pool()
        if not pool:
            return None

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM bluff_matches WHERE id = $1;
                    """,
                    match_id,
                )
                if not row:
                    return None
                return self.row_to_match(dict(row))
        except Exception as e:
            logger.warning(f"Failed to fetch match {match_id} from PostgreSQL: {e}")
            return None

    async def list_open_lobbies(self) -> List[BluffMatch]:
        """Fetch all open lobbies waiting for an opponent from PostgreSQL."""
        pool = get_db_pool()
        if not pool:
            return []

        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM bluff_matches
                    WHERE status = 'WAITING'
                    ORDER BY created_at DESC;
                    """
                )
                return [self.row_to_match(dict(r)) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to list lobbies from PostgreSQL: {e}")
            return []


    # ========================================================================
    # SQLite Direct Persistence (Zero-dependency local persistence & reload testing)
    # ========================================================================

    @staticmethod
    def init_sqlite_schema(conn: sqlite3.Connection) -> None:
        """Initialize schema in SQLite for local process persistence testing."""
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                wallet_address VARCHAR(42) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bluff_matches (
                id VARCHAR(64) PRIMARY KEY,
                creator_id VARCHAR(64),
                opponent_id VARCHAR(64),
                stake_amount NUMERIC NOT NULL DEFAULT 0,
                pot_amount NUMERIC NOT NULL DEFAULT 0,
                creator_secret INT,
                creator_salt VARCHAR(128),
                creator_commitment_hash VARCHAR(64),
                creator_has_committed INTEGER NOT NULL DEFAULT 0,
                creator_action VARCHAR(32),
                creator_action_at TIMESTAMP,
                opponent_secret INT,
                opponent_salt VARCHAR(128),
                opponent_commitment_hash VARCHAR(64),
                opponent_has_committed INTEGER NOT NULL DEFAULT 0,
                opponent_action VARCHAR(32),
                opponent_action_at TIMESTAMP,
                active_turn_player_id VARCHAR(64),
                turn_deadline TIMESTAMP,
                turn_seconds_allowed INT NOT NULL DEFAULT 15,
                winner_id VARCHAR(64),
                status VARCHAR(32) NOT NULL DEFAULT 'WAITING',
                resolution_reason VARCHAR(64),
                payout_tx_hash VARCHAR(128),
                result_payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
            """
        )
        conn.commit()

    @classmethod
    def save_sqlite(cls, conn: sqlite3.Connection, match: BluffMatch) -> None:
        """Persist authoritative BluffMatch state to SQLite."""
        cursor = conn.cursor()
        c_secret = match.creator_commitment.secret_value
        c_salt = match.creator_commitment.salt
        c_hash = match.creator_commitment.commitment_hash
        c_committed = 1 if match.creator_commitment.has_committed else 0
        c_action = match.creator_commitment.action.value if match.creator_commitment.action else None
        c_action_at = match.creator_commitment.action_at.isoformat() if match.creator_commitment.action_at else None

        o_secret = match.opponent_commitment.secret_value if match.opponent_commitment else None
        o_salt = match.opponent_commitment.salt if match.opponent_commitment else None
        o_hash = match.opponent_commitment.commitment_hash if match.opponent_commitment else None
        o_committed = 1 if (match.opponent_commitment and match.opponent_commitment.has_committed) else 0
        o_action = match.opponent_commitment.action.value if (match.opponent_commitment and match.opponent_commitment.action) else None
        o_action_at = match.opponent_commitment.action_at.isoformat() if (match.opponent_commitment and match.opponent_commitment.action_at) else None

        reason = match.resolution_reason.value if match.resolution_reason else None
        result_json = cls._serialize_result_payload(match.result)
        deadline = match.turn_deadline.isoformat() if match.turn_deadline else None
        created = match.created_at.isoformat() if match.created_at else None
        updated = match.updated_at.isoformat() if match.updated_at else None
        resolved = match.resolved_at.isoformat() if match.resolved_at else None

        cursor.execute(
            """
            INSERT INTO bluff_matches (
                id, creator_id, opponent_id, stake_amount, pot_amount,
                creator_secret, creator_salt, creator_commitment_hash, creator_has_committed,
                creator_action, creator_action_at,
                opponent_secret, opponent_salt, opponent_commitment_hash, opponent_has_committed,
                opponent_action, opponent_action_at,
                active_turn_player_id, turn_deadline, turn_seconds_allowed,
                winner_id, status, resolution_reason, payout_tx_hash,
                result_payload, created_at, updated_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                opponent_id = excluded.opponent_id,
                stake_amount = excluded.stake_amount,
                pot_amount = excluded.pot_amount,
                creator_secret = excluded.creator_secret,
                creator_salt = excluded.creator_salt,
                creator_commitment_hash = excluded.creator_commitment_hash,
                creator_has_committed = excluded.creator_has_committed,
                creator_action = excluded.creator_action,
                creator_action_at = excluded.creator_action_at,
                opponent_secret = excluded.opponent_secret,
                opponent_salt = excluded.opponent_salt,
                opponent_commitment_hash = excluded.opponent_commitment_hash,
                opponent_has_committed = excluded.opponent_has_committed,
                opponent_action = excluded.opponent_action,
                opponent_action_at = excluded.opponent_action_at,
                active_turn_player_id = excluded.active_turn_player_id,
                turn_deadline = excluded.turn_deadline,
                turn_seconds_allowed = excluded.turn_seconds_allowed,
                winner_id = excluded.winner_id,
                status = excluded.status,
                resolution_reason = excluded.resolution_reason,
                payout_tx_hash = excluded.payout_tx_hash,
                result_payload = excluded.result_payload,
                updated_at = excluded.updated_at,
                resolved_at = excluded.resolved_at;
            """,
            (
                match.id, match.creator_id, match.opponent_id, float(match.stake_amount), float(match.pot_amount),
                c_secret, c_salt, c_hash, c_committed, c_action, c_action_at,
                o_secret, o_salt, o_hash, o_committed, o_action, o_action_at,
                match.active_turn_player_id, deadline, match.turn_seconds_allowed,
                match.winner_id, match.status.value, reason, match.payout_tx_hash,
                result_json, created, updated, resolved,
            ),
        )
        conn.commit()

    @classmethod
    def get_sqlite(cls, conn: sqlite3.Connection, match_id: str) -> Optional[BluffMatch]:
        """Fetch and reconstruct authoritative BluffMatch from SQLite."""
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bluff_matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return cls.row_to_match(dict(row))

    @classmethod
    def list_open_lobbies_sqlite(cls, conn: sqlite3.Connection) -> List[BluffMatch]:
        """Fetch open lobbies from SQLite."""
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bluff_matches WHERE status = 'WAITING' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [cls.row_to_match(dict(r)) for r in rows]


# Global repository instance
_bluff_repo: Optional[BluffRepository] = None


def get_bluff_repository() -> BluffRepository:
    """Retrieve global BluffRepository instance."""
    global _bluff_repo
    if _bluff_repo is None:
        _bluff_repo = BluffRepository()
    return _bluff_repo
