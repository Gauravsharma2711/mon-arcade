"""
Mon Arcade — Challenge & Bounty Domain Models
Authoritative server-owned state for Arcade Challenges & MON Bounties.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class ChallengeStatus(str, Enum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    CONDITION_MET = "CONDITION_MET"
    CLAIMED = "CLAIMED"
    FAILED = "FAILED"


class ChallengeCondition(str, Enum):
    ATTACKER_WINS = "ATTACKER_WINS"
    WIN_WITHIN_5_TURNS = "WIN_WITHIN_5_TURNS"
    WARDEN_DEFENDS = "WARDEN_DEFENDS"


CONDITION_DESCRIPTIONS = {
    ChallengeCondition.ATTACKER_WINS.value: "Breach the Vault (Attacker triggers fund release)",
    ChallengeCondition.WIN_WITHIN_5_TURNS.value: "Speedrun Breach (Win match in 5 turns or fewer)",
    ChallengeCondition.WARDEN_DEFENDS.value: "Iron Fortress (Warden successfully withstands all 8 turns)",
}


class Challenge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_wallet: str = Field(..., min_length=1, description="Wallet address of the challenge creator")
    game: str = Field("VAULT", description="Target arcade game (only VAULT supported)")
    condition: str = Field(ChallengeCondition.ATTACKER_WINS.value, description="Winning challenge condition")
    bounty_amount: float = Field(..., gt=0, description="Bounty amount in MON")
    status: ChallengeStatus = Field(ChallengeStatus.OPEN, description="Authoritative lifecycle status")
    accepted_by: Optional[str] = Field(None, description="Wallet address of challenger who accepted")
    winner_wallet: Optional[str] = Field(None, description="Wallet address eligible for bounty payout")
    match_id: Optional[str] = Field(None, description="Linked Vault match ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    claimed_at: Optional[datetime] = Field(None, description="Timestamp when bounty was claimed")
    claim_tx_hash: Optional[str] = Field(None, description="Settlement transaction hash")

    @property
    def condition_description(self) -> str:
        return CONDITION_DESCRIPTIONS.get(self.condition, self.condition)


class CreateChallengeRequest(BaseModel):
    creator_wallet: str = Field(..., min_length=1, description="Creator wallet address")
    bounty_amount: float = Field(..., gt=0, description="Bounty reward in MON")
    condition: str = Field(ChallengeCondition.ATTACKER_WINS.value, description="Challenge condition")
    game: str = Field("VAULT", description="Target game (must be VAULT)")


class AcceptChallengeRequest(BaseModel):
    challenger_wallet: str = Field(..., min_length=1, description="Accepting challenger wallet address")


class ClaimBountyRequest(BaseModel):
    claimer_wallet: str = Field(..., min_length=1, description="Claiming winner wallet address")


class ChallengeResponse(BaseModel):
    id: str
    creator_wallet: str
    game: str
    condition: str
    condition_description: str
    bounty_amount: float
    status: ChallengeStatus
    accepted_by: Optional[str] = None
    winner_wallet: Optional[str] = None
    match_id: Optional[str] = None
    created_at: datetime
    claimed_at: Optional[datetime] = None
    claim_tx_hash: Optional[str] = None


def challenge_to_response(ch: Challenge) -> ChallengeResponse:
    return ChallengeResponse(
        id=ch.id,
        creator_wallet=ch.creator_wallet,
        game=ch.game,
        condition=ch.condition,
        condition_description=ch.condition_description,
        bounty_amount=ch.bounty_amount,
        status=ch.status,
        accepted_by=ch.accepted_by,
        winner_wallet=ch.winner_wallet,
        match_id=ch.match_id,
        created_at=ch.created_at,
        claimed_at=ch.claimed_at,
        claim_tx_hash=ch.claim_tx_hash,
    )
