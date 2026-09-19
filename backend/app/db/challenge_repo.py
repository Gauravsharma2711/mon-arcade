"""
Mon Arcade — Challenge Repository
Dual-mode persistence for Arcade Challenges & MON Bounties.
Gracefully operates with in-memory storage when PostgreSQL is offline.
"""

from datetime import datetime, timezone
import logging
from typing import Optional, List, Dict, Any

from backend.app.db.database import get_db_pool
from backend.app.game.challenge_models import (
    Challenge,
    ChallengeStatus,
    ChallengeCondition,
)

logger = logging.getLogger("mon_arcade.challenge.repo")


class ChallengeRepository:
    """Repository handling persistence for Mon Arcade Challenges."""

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        self._challenges: Dict[str, Challenge] = {}
        self._seed_default_challenges()

    def _seed_default_challenges(self):
        """Seed realistic demo challenges for local exploration."""
        seeds = [
            Challenge(
                id="challenge-vault-speedrun",
                creator_wallet="0x89C4A53B91f24e9A6b6B24a9A12B104c3B84A91b",
                game="VAULT",
                condition=ChallengeCondition.WIN_WITHIN_5_TURNS.value,
                bounty_amount=100.0,
                status=ChallengeStatus.OPEN,
                created_at=datetime.now(timezone.utc),
            ),
            Challenge(
                id="challenge-sentinel-breach",
                creator_wallet="0x33B19aF91C8A53B91f24e9A6b6B24a9A12B148F2",
                game="VAULT",
                condition=ChallengeCondition.ATTACKER_WINS.value,
                bounty_amount=50.0,
                status=ChallengeStatus.OPEN,
                created_at=datetime.now(timezone.utc),
            ),
            Challenge(
                id="challenge-ironclad-defense",
                creator_wallet="0x55E96cB3104c3B8449b289C4A53B91f24e9A91A0",
                game="VAULT",
                condition=ChallengeCondition.WARDEN_DEFENDS.value,
                bounty_amount=75.0,
                status=ChallengeStatus.OPEN,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        for s in seeds:
            self._challenges[s.id] = s

    async def save_challenge(self, challenge: Challenge) -> Challenge:
        """Persist or update a challenge."""
        self._challenges[challenge.id] = challenge
        pool = self._db_pool or get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO arcade_challenges (
                            id, creator_wallet, game, condition, bounty_amount,
                            status, accepted_by, winner_wallet, match_id,
                            created_at, claimed_at, claim_tx_hash
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            accepted_by = EXCLUDED.accepted_by,
                            winner_wallet = EXCLUDED.winner_wallet,
                            match_id = EXCLUDED.match_id,
                            claimed_at = EXCLUDED.claimed_at,
                            claim_tx_hash = EXCLUDED.claim_tx_hash;
                        """,
                        challenge.id,
                        challenge.creator_wallet,
                        challenge.game,
                        challenge.condition,
                        challenge.bounty_amount,
                        challenge.status.value if isinstance(challenge.status, ChallengeStatus) else str(challenge.status),
                        challenge.accepted_by,
                        challenge.winner_wallet,
                        challenge.match_id,
                        challenge.created_at,
                        challenge.claimed_at,
                        challenge.claim_tx_hash,
                    )
            except Exception as e:
                logger.warning(f"Failed to persist challenge '{challenge.id}' to PostgreSQL: {e}")
        return challenge

    async def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Fetch a challenge by ID."""
        pool = self._db_pool or get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM arcade_challenges WHERE id = $1", challenge_id
                    )
                    if row:
                        return Challenge(
                            id=row["id"],
                            creator_wallet=row["creator_wallet"],
                            game=row["game"],
                            condition=row["condition"],
                            bounty_amount=float(row["bounty_amount"]),
                            status=ChallengeStatus(row["status"]),
                            accepted_by=row["accepted_by"],
                            winner_wallet=row["winner_wallet"],
                            match_id=row["match_id"],
                            created_at=row["created_at"],
                            claimed_at=row["claimed_at"],
                            claim_tx_hash=row["claim_tx_hash"],
                        )
            except Exception as e:
                logger.warning(f"Failed to query challenge '{challenge_id}' from DB: {e}")

        return self._challenges.get(challenge_id)

    async def list_challenges(self, status: Optional[ChallengeStatus] = None) -> List[Challenge]:
        """List challenges, optionally filtered by status."""
        pool = self._db_pool or get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    if status:
                        val = status.value if isinstance(status, ChallengeStatus) else str(status)
                        rows = await conn.fetch(
                            "SELECT * FROM arcade_challenges WHERE status = $1 ORDER BY created_at DESC",
                            val,
                        )
                    else:
                        rows = await conn.fetch(
                            "SELECT * FROM arcade_challenges ORDER BY created_at DESC"
                        )
                    return [
                        Challenge(
                            id=r["id"],
                            creator_wallet=r["creator_wallet"],
                            game=r["game"],
                            condition=r["condition"],
                            bounty_amount=float(r["bounty_amount"]),
                            status=ChallengeStatus(r["status"]),
                            accepted_by=r["accepted_by"],
                            winner_wallet=r["winner_wallet"],
                            match_id=r["match_id"],
                            created_at=r["created_at"],
                            claimed_at=r["claimed_at"],
                            claim_tx_hash=r["claim_tx_hash"],
                        )
                        for r in rows
                    ]
            except Exception as e:
                logger.warning(f"Failed to list challenges from DB: {e}")

        items = list(self._challenges.values())
        if status:
            items = [c for c in items if c.status == status]
        return sorted(items, key=lambda c: c.created_at, reverse=True)


default_challenge_repo = ChallengeRepository()
