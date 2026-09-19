"""
Mon Arcade — First Blood / Early Arcade Player Repository
Dual-mode persistence: in-memory store for offline/test environments,
PostgreSQL when pool is active.

Guarantees:
- Creates a first-player record if one does not exist
- Preserves the original first_participation_at timestamp
- Never duplicates the record for the same wallet
- Incremental player number if supported
"""

from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Tuple
from pydantic import BaseModel, Field

from backend.app.db.database import get_db_pool

logger = logging.getLogger("mon_arcade.first_blood.repo")


class FirstBloodRecord(BaseModel):
    wallet: str
    first_participation_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    player_number: Optional[int] = None
    first_game: str = "VAULT"
    is_first_time: bool = False


class FirstBloodRepository:
    """Authoritative repository for Early Arcade Player participation records."""

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        self._records: Dict[str, FirstBloodRecord] = {}
        self._counter = 0

    def _normalize_wallet(self, wallet: str) -> str:
        return wallet.strip().lower()

    async def record_participation(
        self, wallet: str, game: str = "VAULT"
    ) -> Tuple[FirstBloodRecord, bool]:
        """
        Record participation for a wallet.
        If already recorded, returns existing record with is_first_time=False.
        If new, saves new record with is_first_time=True.
        """
        norm_wallet = self._normalize_wallet(wallet)
        pool = self._db_pool or get_db_pool()

        if pool:
            try:
                async with pool.acquire() as conn:
                    # Check existing first
                    row = await conn.fetchrow(
                        "SELECT wallet, first_participation_at, player_number, first_game FROM first_blood_players WHERE LOWER(wallet) = $1",
                        norm_wallet,
                    )
                    if row:
                        rec = FirstBloodRecord(
                            wallet=row["wallet"],
                            first_participation_at=row["first_participation_at"],
                            player_number=row["player_number"],
                            first_game=row["first_game"],
                            is_first_time=False,
                        )
                        self._records[norm_wallet] = rec
                        return rec, False

                    # Insert new record
                    inserted = await conn.fetchrow(
                        """
                        INSERT INTO first_blood_players (wallet, first_participation_at, first_game)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (wallet) DO NOTHING
                        RETURNING wallet, first_participation_at, player_number, first_game;
                        """,
                        wallet.strip(),
                        datetime.now(timezone.utc),
                        game.upper(),
                    )
                    if inserted:
                        rec = FirstBloodRecord(
                            wallet=inserted["wallet"],
                            first_participation_at=inserted["first_participation_at"],
                            player_number=inserted["player_number"],
                            first_game=inserted["first_game"],
                            is_first_time=True,
                        )
                        self._records[norm_wallet] = rec
                        return rec, True
                    else:
                        # Conflict occurred in parallel; fetch existing
                        existing = await conn.fetchrow(
                            "SELECT wallet, first_participation_at, player_number, first_game FROM first_blood_players WHERE LOWER(wallet) = $1",
                            norm_wallet,
                        )
                        if existing:
                            rec = FirstBloodRecord(
                                wallet=existing["wallet"],
                                first_participation_at=existing["first_participation_at"],
                                player_number=existing["player_number"],
                                first_game=existing["first_game"],
                                is_first_time=False,
                            )
                            self._records[norm_wallet] = rec
                            return rec, False
            except Exception as e:
                logger.warning(f"Failed to record First Blood in PostgreSQL: {e}")

        # In-memory fallback
        if norm_wallet in self._records:
            existing = self._records[norm_wallet]
            return existing, False

        self._counter += 1
        rec = FirstBloodRecord(
            wallet=wallet.strip(),
            first_participation_at=datetime.now(timezone.utc),
            player_number=self._counter,
            first_game=game.upper(),
            is_first_time=True,
        )
        self._records[norm_wallet] = rec
        return rec, True

    async def get_record(self, wallet: str) -> Optional[FirstBloodRecord]:
        """Fetch First Blood record for wallet if exists."""
        norm_wallet = self._normalize_wallet(wallet)
        pool = self._db_pool or get_db_pool()

        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT wallet, first_participation_at, player_number, first_game FROM first_blood_players WHERE LOWER(wallet) = $1",
                        norm_wallet,
                    )
                    if row:
                        rec = FirstBloodRecord(
                            wallet=row["wallet"],
                            first_participation_at=row["first_participation_at"],
                            player_number=row["player_number"],
                            first_game=row["first_game"],
                            is_first_time=False,
                        )
                        self._records[norm_wallet] = rec
                        return rec
            except Exception as e:
                logger.warning(f"Failed to query First Blood from DB: {e}")

        return self._records.get(norm_wallet)


default_first_blood_repo = FirstBloodRepository()
