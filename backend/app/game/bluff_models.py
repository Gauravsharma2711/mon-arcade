"""
Authoritative Server-Side Domain Models for Bluff or Bust.

Defines the state machine, player commitments, authoritative timing,
and client state sanitization for 1v1 hidden-information duels.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class BluffMatchStatus(str, Enum):
    """Authoritative lifecycle states of a Bluff or Bust match."""
    WAITING = "WAITING"        # Match created by host; waiting for opponent to join and commit
    ACTIVE = "ACTIVE"          # Both players joined; secrets committed; preparing round
    DECISION = "DECISION"      # Turn clock active; waiting for Push or Fold decision
    REVEALING = "REVEALING"    # Action submitted; cards being revealed
    RESOLVED = "RESOLVED"      # Winner determined; pot distributed; showdown complete
    CANCELLED = "CANCELLED"    # Aborted before match commenced


class BluffAction(str, Enum):
    """Player actions during the decision phase."""
    PUSH = "PUSH"  # Challenge / showdown: call the bluff
    FOLD = "FOLD"  # Surrender / retreat: yield the pot to the opponent


class BluffResolutionReason(str, Enum):
    """Authoritative reason for match outcome."""
    SHOWDOWN_HIGHER_CARD = "SHOWDOWN_HIGHER_CARD"
    SHOWDOWN_TIE = "SHOWDOWN_TIE"
    CREATOR_FOLDED = "CREATOR_FOLDED"
    OPPONENT_FOLDED = "OPPONENT_FOLDED"
    CREATOR_TIMEOUT = "CREATOR_TIMEOUT"
    OPPONENT_TIMEOUT = "OPPONENT_TIMEOUT"


class PlayerCommitment(BaseModel):
    """Individual player commitment state."""
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    secret_value: Optional[int] = Field(None, ge=1, le=10)  # Hidden value 1 to 10
    salt: Optional[str] = None                             # Cryptographically secure random salt
    commitment_hash: Optional[str] = None                  # SHA-256(secret:salt)
    has_committed: bool = False
    committed_at: Optional[datetime] = None
    action: Optional[BluffAction] = None
    action_at: Optional[datetime] = None


class PlayerClientView(BaseModel):
    """Sanitized view of a player for client consumption."""
    player_id: str
    commitment_hash: Optional[str] = None                  # Public commitment hash for verification
    secret_value: Optional[int] = None                     # None if hidden from observer
    salt: Optional[str] = None                             # None if hidden from observer
    has_committed: bool
    action: Optional[BluffAction] = None


class BluffSettlementStatus(str, Enum):
    """Settlement status for Bluff or Bust match outcomes."""
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class RevealedPlayerValue(BaseModel):
    """Authoritative revealed values and commitment verification for a player."""
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    secret_value: int
    salt: str
    commitment_hash: str
    commitment_verified: bool
    action: Optional[BluffAction] = None


class BluffMatchResult(BaseModel):
    """
    Authoritative resolution result for a Bluff or Bust match.
    Supports winner, loser, revealed values, decisions, match result, and settlement.
    """
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    status: BluffMatchStatus = BluffMatchStatus.RESOLVED
    winner_id: Optional[str] = None
    loser_id: Optional[str] = None
    is_tie: bool = False
    resolution_reason: BluffResolutionReason
    creator_revealed: RevealedPlayerValue
    opponent_revealed: RevealedPlayerValue
    pot_amount: Decimal
    payout_tx_hash: Optional[str] = None
    settlement_status: BluffSettlementStatus = BluffSettlementStatus.SETTLED
    resolved_at: datetime


class BluffMatchClientView(BaseModel):
    """
    Sanitized match representation sent to frontend clients.
    
    Guarantees:
    - Frontend NEVER sees opponent's secret_value until status is RESOLVED.
    - Frontend receives authoritative countdown, status, and turn indicators.
    - Frontend can restore state completely upon reconnect or page refresh.
    """
    id: str
    creator: PlayerClientView
    opponent: Optional[PlayerClientView] = None
    stake_amount: Decimal
    pot_amount: Decimal
    status: BluffMatchStatus
    active_turn_player_id: Optional[str] = None
    turn_seconds_allowed: int
    seconds_remaining: int
    can_act: bool
    is_creator: bool
    winner_id: Optional[str] = None
    resolution_reason: Optional[BluffResolutionReason] = None
    payout_tx_hash: Optional[str] = None
    result: Optional[BluffMatchResult] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class BluffMatch(BaseModel):
    """
    Authoritative server-side domain entity for a Bluff match.
    Owns authoritative game logic, hidden values, timing, and resolution.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: str
    opponent_id: Optional[str] = None
    stake_amount: Decimal = Decimal("5.0")
    pot_amount: Decimal = Decimal("10.0")
    status: BluffMatchStatus = BluffMatchStatus.WAITING

    creator_commitment: PlayerCommitment
    opponent_commitment: Optional[PlayerCommitment] = None

    active_turn_player_id: Optional[str] = None
    turn_deadline: Optional[datetime] = None
    turn_seconds_allowed: int = 15

    winner_id: Optional[str] = None
    resolution_reason: Optional[BluffResolutionReason] = None
    payout_tx_hash: Optional[str] = None
    result: Optional[BluffMatchResult] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None

    def seconds_remaining(self) -> int:
        """Calculate authoritative seconds remaining on current turn countdown."""
        if not self.turn_deadline or self.status not in (BluffMatchStatus.ACTIVE, BluffMatchStatus.DECISION):
            return 0
        now = datetime.now(timezone.utc)
        remaining = int((self.turn_deadline - now).total_seconds())
        return max(0, remaining)

    def is_expired(self) -> bool:
        """Check if active turn deadline has elapsed."""
        if not self.turn_deadline:
            return False
        return datetime.now(timezone.utc) >= self.turn_deadline

    def verify_commitment_integrity(self, player_id: str) -> bool:
        """Verify that a player's revealed secret and salt match their stored commitment hash."""
        from backend.app.game.bluff_crypto import verify_commitment

        target: Optional[PlayerCommitment] = None
        if self.creator_commitment.player_id == player_id:
            target = self.creator_commitment
        elif self.opponent_commitment and self.opponent_commitment.player_id == player_id:
            target = self.opponent_commitment

        if not target or target.secret_value is None or not target.salt or not target.commitment_hash:
            return False

        return verify_commitment(target.secret_value, target.salt, target.commitment_hash)

    def to_client_view(self, viewer_id: Optional[str] = None) -> BluffMatchClientView:
        """
        Sanitize server state for a specific player or spectator.
        
        The opponent's secret value and salt are strictly omitted unless the match is RESOLVED.
        The commitment hash is always public so commitment can be audited.
        """
        is_resolved = self.status == BluffMatchStatus.RESOLVED

        # Creator view
        creator_view = PlayerClientView(
            player_id=self.creator_commitment.player_id,
            commitment_hash=self.creator_commitment.commitment_hash,
            secret_value=(
                self.creator_commitment.secret_value
                if (viewer_id == self.creator_id or is_resolved)
                else None
            ),
            salt=(
                self.creator_commitment.salt
                if (viewer_id == self.creator_id or is_resolved)
                else None
            ),
            has_committed=self.creator_commitment.has_committed,
            action=self.creator_commitment.action,
        )

        # Opponent view
        opponent_view: Optional[PlayerClientView] = None
        if self.opponent_commitment:
            opponent_view = PlayerClientView(
                player_id=self.opponent_commitment.player_id,
                commitment_hash=self.opponent_commitment.commitment_hash,
                secret_value=(
                    self.opponent_commitment.secret_value
                    if (viewer_id == self.opponent_id or is_resolved)
                    else None
                ),
                salt=(
                    self.opponent_commitment.salt
                    if (viewer_id == self.opponent_id or is_resolved)
                    else None
                ),
                has_committed=self.opponent_commitment.has_committed,
                action=self.opponent_commitment.action,
            )

        # Action permissions
        can_act = (
            self.status == BluffMatchStatus.DECISION
            and viewer_id is not None
            and viewer_id == self.active_turn_player_id
            and not self.is_expired()
        )

        return BluffMatchClientView(
            id=self.id,
            creator=creator_view,
            opponent=opponent_view,
            stake_amount=self.stake_amount,
            pot_amount=self.pot_amount,
            status=self.status,
            active_turn_player_id=self.active_turn_player_id,
            turn_seconds_allowed=self.turn_seconds_allowed,
            seconds_remaining=self.seconds_remaining(),
            can_act=can_act,
            is_creator=(viewer_id == self.creator_id),
            winner_id=self.winner_id,
            resolution_reason=self.resolution_reason,
            payout_tx_hash=self.payout_tx_hash,
            result=self.result if is_resolved else None,
            created_at=self.created_at,
            resolved_at=self.resolved_at,
        )
