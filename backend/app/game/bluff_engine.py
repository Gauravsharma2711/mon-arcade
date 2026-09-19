"""
Authoritative Server-Side Game Engine for Bluff or Bust.

Owns the complete 1v1 hidden-information duel lifecycle:
1. Match created (host posts stake and secret commitment)
2. Player joins (opponent posts stake and secret commitment)
3. Players prepare hidden values & commitments are recorded
4. Match enters decision phase with authoritative turn countdown
5. Active player submits Push or Fold decision
6. Decisions are stored server-side
7. Reveal phase begins
8. Cryptographic commitments are recalculated and verified
9. Server deterministically resolves match outcome (higher card wins, fold yields, tie refunds)
10. Result is structured independently from monetary settlement
11. State is sanitized and returned to clients

Security Guarantees:
- React NEVER calculates or decides winners.
- Opponent secret values and salts remain masked until RESOLVED.
- Cryptographic verification rejects altered secrets or salts.
- Deterministic outcome resolution.
"""

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import secrets
from typing import Optional, Union, Dict, List, Tuple, Any
import uuid

logger = logging.getLogger(__name__)

from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffResolutionReason,
    BluffSettlementStatus,
    RevealedPlayerValue,
    BluffMatchResult,
    PlayerCommitment,
    BluffMatchClientView,
    BluffMatch,
)
from backend.app.game.bluff_crypto import (
    generate_salt,
    generate_secret_value,
    create_commitment,
    verify_commitment,
)


# ============================================================================
# Engine Exceptions
# ============================================================================

class BluffEngineError(Exception):
    """Base exception for all Bluff game engine errors."""
    pass


class MatchNotFoundError(BluffEngineError):
    """Raised when the requested match ID does not exist."""
    pass


class InvalidStateTransitionError(BluffEngineError):
    """Raised when an operation is invalid for the current match lifecycle state."""
    pass


class UnauthorizedPlayerError(BluffEngineError):
    """Raised when a player attempts an action they are not permitted to perform."""
    pass


class InvalidDecisionError(BluffEngineError):
    """Raised when an unrecognized or invalid player decision is submitted."""
    pass


class InvalidSecretValueError(BluffEngineError):
    """Raised when a secret card value is outside the permitted bounds (1-10)."""
    pass


class CommitmentVerificationError(BluffEngineError):
    """Raised when secret value + salt fails cryptographic verification against commitment hash."""
    pass


class MatchAlreadyResolvedError(BluffEngineError):
    """Raised when an action is attempted on an already RESOLVED or CANCELLED match."""
    pass


# ============================================================================
# In-Memory & Persistent Match Store
# ============================================================================

class BluffMatchStore:
    """
    Match store for active Bluff matches.
    Provides fast in-memory access with automatic fallback to PostgreSQL/database persistence
    to support session restoration after reconnects, page refreshes, and process reloads.
    """

    def __init__(self, repo: Optional[Any] = None) -> None:
        self._matches: Dict[str, BluffMatch] = {}
        self._repo = repo
        self._sqlite_conn: Optional[sqlite3.Connection] = None

    def set_sqlite_connection(self, conn: sqlite3.Connection) -> None:
        """Register a SQLite connection for local process-reload persistence testing."""
        self._sqlite_conn = conn

    def save(self, match: BluffMatch) -> BluffMatch:
        """Save match to memory and persist to database if available."""
        match.updated_at = datetime.now(timezone.utc)
        self._matches[match.id] = match

        # Synchronous SQLite persistence if registered
        if self._sqlite_conn:
            try:
                from backend.app.db.bluff_repo import BluffRepository
                BluffRepository.save_sqlite(self._sqlite_conn, match)
            except Exception as e:
                logger.warning(f"Failed to persist match {match.id} to SQLite: {e}")

        # Async PostgreSQL persistence if event loop is active
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            if loop.is_running():
                from backend.app.db.bluff_repo import get_bluff_repository
                repo = self._repo or get_bluff_repository()
                loop.create_task(repo.save(match))
        except RuntimeError:
            pass  # No running event loop in synchronous context

        return match

    async def save_async(self, match: BluffMatch) -> BluffMatch:
        """Explicitly await persistence to database."""
        match.updated_at = datetime.now(timezone.utc)
        self._matches[match.id] = match
        if self._sqlite_conn:
            from backend.app.db.bluff_repo import BluffRepository
            BluffRepository.save_sqlite(self._sqlite_conn, match)
        from backend.app.db.bluff_repo import get_bluff_repository
        repo = self._repo or get_bluff_repository()
        await repo.save(match)
        return match

    def get(self, match_id: str) -> Optional[BluffMatch]:
        """
        Retrieve match from memory. If missing (e.g. after process reload),
        attempts restoration from registered SQLite or PostgreSQL repository.
        """
        match = self._matches.get(match_id)
        if match:
            return match

        # Attempt restoration from SQLite if registered
        if self._sqlite_conn:
            try:
                from backend.app.db.bluff_repo import BluffRepository
                restored = BluffRepository.get_sqlite(self._sqlite_conn, match_id)
                if restored:
                    self._matches[restored.id] = restored
                    return restored
            except Exception as e:
                logger.warning(f"Failed to restore match {match_id} from SQLite: {e}")

        return None

    async def get_async(self, match_id: str) -> Optional[BluffMatch]:
        """Asynchronously retrieve match from memory or database."""
        match = self.get(match_id)
        if match:
            return match

        from backend.app.db.bluff_repo import get_bluff_repository
        repo = self._repo or get_bluff_repository()
        restored = await repo.get(match_id)
        if restored:
            self._matches[restored.id] = restored
            return restored
        return None

    def list_open_lobbies(self) -> List[BluffMatch]:
        """Returns all matches currently waiting for an opponent."""
        # If in-memory is empty and SQLite is registered, restore open lobbies
        if not self._matches and self._sqlite_conn:
            from backend.app.db.bluff_repo import BluffRepository
            restored_list = BluffRepository.list_open_lobbies_sqlite(self._sqlite_conn)
            for m in restored_list:
                self._matches[m.id] = m

        return [m for m in self._matches.values() if m.status == BluffMatchStatus.WAITING]

    def clear(self) -> None:
        """Clear the in-memory cache (simulates server restart/reboot)."""
        self._matches.clear()


# ============================================================================
# Authoritative Game Engine
# ============================================================================

class BluffGameEngine:
    """
    Authoritative server-side game engine for Bluff or Bust.
    Enforces rules, transitions, reveal verification, and deterministic resolutions.
    """

    def __init__(self, store: Optional[BluffMatchStore] = None) -> None:
        self.store = store or BluffMatchStore()

    def create_match(
        self,
        creator_id: str,
        stake_amount: Decimal = Decimal("5.0"),
        secret_value: Optional[int] = None,
        salt: Optional[str] = None,
        turn_seconds: int = 15,
        match_id: Optional[str] = None,
    ) -> BluffMatch:
        """
        Create a new Bluff duel match.
        Creator may provide a secret value immediately or commit it in a subsequent step.
        """
        if not creator_id or not creator_id.strip():
            raise UnauthorizedPlayerError("Creator ID must be a non-empty string.")

        if stake_amount <= Decimal("0"):
            raise ValueError("Stake amount must be strictly greater than 0.")

        if turn_seconds < 5:
            raise ValueError("Turn seconds allowed must be at least 5 seconds.")

        m_id = match_id or f"bluff_{uuid.uuid4().hex[:8]}"

        # Initialize creator commitment
        if secret_value is not None:
            self._validate_secret_value(secret_value)
            used_salt = salt or generate_salt()
            comm_hash = create_commitment(secret_value, used_salt)
            creator_commitment = PlayerCommitment(
                player_id=creator_id,
                secret_value=secret_value,
                salt=used_salt,
                commitment_hash=comm_hash,
                has_committed=True,
                committed_at=datetime.now(timezone.utc),
            )
        else:
            creator_commitment = PlayerCommitment(
                player_id=creator_id,
                has_committed=False,
            )

        match = BluffMatch(
            id=m_id,
            creator_id=creator_id,
            stake_amount=stake_amount,
            pot_amount=stake_amount * Decimal("2"),
            status=BluffMatchStatus.WAITING,
            creator_commitment=creator_commitment,
            turn_seconds_allowed=turn_seconds,
        )

        return self.store.save(match)

    def prepare_secret(self, secret_value: Optional[int] = None) -> Tuple[int, str, str]:
        """
        Helper to generate or prepare secret value, salt, and commitment hash.
        Returns (secret_value, salt, commitment_hash).
        """
        if secret_value is not None:
            self._validate_secret_value(secret_value)
            val = secret_value
        else:
            val = generate_secret_value()

        salt = generate_salt()
        commitment_hash = create_commitment(val, salt)
        return val, salt, commitment_hash

    def commit_secret(
        self,
        match_id: str,
        player_id: str,
        secret_value: int,
        salt: Optional[str] = None,
    ) -> BluffMatch:
        """
        Record a player's secret value commitment before the decision phase begins.
        """
        match = self._get_match_or_raise(match_id)

        if match.status in (BluffMatchStatus.RESOLVED, BluffMatchStatus.CANCELLED):
            raise MatchAlreadyResolvedError(
                f"Cannot commit secret: match {match_id} is already {match.status.value}."
            )

        if match.status not in (BluffMatchStatus.WAITING, BluffMatchStatus.ACTIVE):
            raise InvalidStateTransitionError(
                f"Cannot commit secret in state {match.status.value}."
            )

        if player_id != match.creator_id and (not match.opponent_id or player_id != match.opponent_id):
            raise UnauthorizedPlayerError(f"Player {player_id} is not a participant in match {match_id}.")

        self._validate_secret_value(secret_value)
        used_salt = salt or generate_salt()
        comm_hash = create_commitment(secret_value, used_salt)
        now = datetime.now(timezone.utc)

        if player_id == match.creator_id:
            if match.creator_commitment.has_committed:
                raise InvalidStateTransitionError("Creator has already committed a secret value.")
            match.creator_commitment.secret_value = secret_value
            match.creator_commitment.salt = used_salt
            match.creator_commitment.commitment_hash = comm_hash
            match.creator_commitment.has_committed = True
            match.creator_commitment.committed_at = now
        else:
            if match.opponent_commitment and match.opponent_commitment.has_committed:
                raise InvalidStateTransitionError("Opponent has already committed a secret value.")
            match.opponent_commitment = PlayerCommitment(
                player_id=player_id,
                secret_value=secret_value,
                salt=used_salt,
                commitment_hash=comm_hash,
                has_committed=True,
                committed_at=now,
            )

        # Check if match is ready to transition to DECISION
        self._evaluate_readiness_for_decision(match)
        return self.store.save(match)

    def join_match(
        self,
        match_id: str,
        opponent_id: str,
        secret_value: Optional[int] = None,
        salt: Optional[str] = None,
    ) -> BluffMatch:
        """
        An opponent joins an open Bluff duel.
        Opponent can optionally submit secret value upon joining.
        """
        match = self._get_match_or_raise(match_id)

        if match.status in (BluffMatchStatus.RESOLVED, BluffMatchStatus.CANCELLED):
            raise MatchAlreadyResolvedError(
                f"Cannot join match {match_id}: match is already {match.status.value}."
            )

        if match.status != BluffMatchStatus.WAITING:
            raise InvalidStateTransitionError(
                f"Cannot join match {match_id}: status is {match.status.value}, expected WAITING."
            )

        if not opponent_id or not opponent_id.strip():
            raise UnauthorizedPlayerError("Opponent ID must be a non-empty string.")

        if opponent_id == match.creator_id:
            raise UnauthorizedPlayerError("Creator cannot join their own match as an opponent.")

        match.opponent_id = opponent_id
        now = datetime.now(timezone.utc)

        if secret_value is not None:
            self._validate_secret_value(secret_value)
            used_salt = salt or generate_salt()
            comm_hash = create_commitment(secret_value, used_salt)
            match.opponent_commitment = PlayerCommitment(
                player_id=opponent_id,
                secret_value=secret_value,
                salt=used_salt,
                commitment_hash=comm_hash,
                has_committed=True,
                committed_at=now,
            )
        else:
            match.opponent_commitment = PlayerCommitment(
                player_id=opponent_id,
                has_committed=False,
            )

        # Transition state
        self._evaluate_readiness_for_decision(match)
        return self.store.save(match)

    def submit_action(
        self,
        match_id: str,
        player_id: str,
        action: Union[BluffAction, str],
    ) -> BluffMatch:
        """
        Active player submits PUSH (challenge) or FOLD (yield).
        Server records decision, triggers reveal & verification, and deterministically resolves the match.
        """
        match = self._get_match_or_raise(match_id)

        if match.status in (BluffMatchStatus.RESOLVED, BluffMatchStatus.CANCELLED):
            raise MatchAlreadyResolvedError(
                f"Cannot submit action: match {match_id} is already {match.status.value}."
            )

        if match.status != BluffMatchStatus.DECISION:
            raise InvalidStateTransitionError(
                f"Cannot submit action in state {match.status.value}: must be in DECISION."
            )

        # Validate player participation
        if player_id not in (match.creator_id, match.opponent_id):
            raise UnauthorizedPlayerError(
                f"Player {player_id} is not an authorized participant in match {match_id}."
            )

        # Validate turn authority (allow human player to act if opponent is a simulated bot)
        is_vs_bot = bool(
            (match.opponent_id and match.opponent_id.startswith("0xsimulated"))
            or (match.creator_id and match.creator_id.startswith("0xsimulated"))
        )
        is_human_participant = bool(
            player_id in (match.creator_id, match.opponent_id)
            and not player_id.startswith("0xsimulated")
        )
        if player_id != match.active_turn_player_id and not (is_vs_bot and is_human_participant):
            raise UnauthorizedPlayerError(
                f"It is not player {player_id}'s turn to act (active: {match.active_turn_player_id})."
            )

        # Validate action
        parsed_action = self._parse_action(action)
        now = datetime.now(timezone.utc)

        # Validate against duplicate action
        if player_id == match.creator_id and match.creator_commitment.action is not None:
            raise InvalidStateTransitionError("Creator has already submitted an action for this round.")
        if player_id == match.opponent_id and match.opponent_commitment and match.opponent_commitment.action is not None:
            raise InvalidStateTransitionError("Opponent has already submitted an action for this round.")

        # Store action on server
        if player_id == match.creator_id:
            match.creator_commitment.action = parsed_action
            match.creator_commitment.action_at = now
        elif match.opponent_commitment:
            match.opponent_commitment.action = parsed_action
            match.opponent_commitment.action_at = now

        # Enter REVEALING phase
        match.status = BluffMatchStatus.REVEALING

        # Authoritatively reveal, verify cryptographic commitments, and resolve
        self._reveal_and_resolve(match, triggered_by_action=parsed_action)
        return self.store.save(match)

    def handle_timeout(self, match_id: str) -> BluffMatch:
        """
        Authoritative turn timeout resolution.
        If the active player's turn deadline has elapsed, that player automatically forfeits.
        """
        match = self._get_match_or_raise(match_id)

        if match.status in (BluffMatchStatus.RESOLVED, BluffMatchStatus.CANCELLED):
            raise MatchAlreadyResolvedError(
                f"Cannot handle timeout: match {match_id} is already {match.status.value}."
            )

        if match.status != BluffMatchStatus.DECISION:
            raise InvalidStateTransitionError(
                f"Cannot timeout match in state {match.status.value}: must be in DECISION."
            )

        if not match.is_expired():
            raise InvalidStateTransitionError(
                f"Turn deadline has not elapsed yet ({match.seconds_remaining()}s remaining)."
            )

        match.status = BluffMatchStatus.REVEALING
        self._reveal_and_resolve(match, timed_out_player_id=match.active_turn_player_id)
        return self.store.save(match)

    def cancel_match(self, match_id: str, player_id: str) -> BluffMatch:
        """
        Creator cancels an open match before an opponent joins.
        """
        match = self._get_match_or_raise(match_id)

        if match.status in (BluffMatchStatus.RESOLVED, BluffMatchStatus.CANCELLED):
            raise MatchAlreadyResolvedError(
                f"Cannot cancel match {match_id}: match is already {match.status.value}."
            )

        if match.status != BluffMatchStatus.WAITING:
            raise InvalidStateTransitionError(
                f"Cannot cancel match in state {match.status.value}: opponent has already joined."
            )

        if player_id != match.creator_id:
            raise UnauthorizedPlayerError("Only the match creator can cancel an open lobby.")

        match.status = BluffMatchStatus.CANCELLED
        return self.store.save(match)

    def get_match(self, match_id: str) -> BluffMatch:
        """Retrieve full authoritative match state."""
        return self._get_match_or_raise(match_id)

    def get_client_view(self, match_id: str, viewer_id: Optional[str] = None) -> BluffMatchClientView:
        """
        Retrieve sanitized client view for a specific player or spectator.
        Guarantees opponent secrets and salts remain hidden until RESOLVED.
        Automatically authoritatively resolves turn timeout if deadline elapsed.
        """
        match = self._get_match_or_raise(match_id)
        if match.status == BluffMatchStatus.DECISION and match.is_expired():
            match = self.handle_timeout(match_id)
        return match.to_client_view(viewer_id)

    # ========================================================================
    # Private Helpers & Resolution Logic
    # ========================================================================

    def _get_match_or_raise(self, match_id: str) -> BluffMatch:
        match = self.store.get(match_id)
        if not match:
            raise MatchNotFoundError(f"Match with ID '{match_id}' was not found.")
        return match

    @staticmethod
    def _validate_secret_value(value: int) -> None:
        if not isinstance(value, int) or value < 1 or value > 10:
            raise InvalidSecretValueError(
                f"Secret card value must be an integer between 1 and 10 (received {value})."
            )

    @staticmethod
    def _parse_action(action: Union[BluffAction, str]) -> BluffAction:
        if isinstance(action, BluffAction):
            return action
        if isinstance(action, str):
            try:
                return BluffAction(action.upper())
            except ValueError:
                raise InvalidDecisionError(
                    f"Invalid bluff action '{action}'. Permitted actions: {[a.value for a in BluffAction]}"
                )
        raise InvalidDecisionError(f"Action must be a BluffAction enum or string, got {type(action)}.")

    def _evaluate_readiness_for_decision(self, match: BluffMatch) -> None:
        """
        Transition match to DECISION if both creator and opponent have committed secrets.
        Otherwise transition to ACTIVE if opponent has joined.
        """
        has_opponent = match.opponent_id is not None and match.opponent_commitment is not None
        creator_ready = match.creator_commitment.has_committed
        opponent_ready = has_opponent and match.opponent_commitment.has_committed

        if creator_ready and opponent_ready:
            match.status = BluffMatchStatus.DECISION
            # When playing against a simulated bot, assign the initial decision turn to the human player
            if match.opponent_id and match.opponent_id.startswith("0xsimulated"):
                match.active_turn_player_id = match.creator_id
            elif match.creator_id and match.creator_id.startswith("0xsimulated"):
                match.active_turn_player_id = match.opponent_id
            else:
                match.active_turn_player_id = match.opponent_id  # Challenger holds initial action turn
            now = datetime.now(timezone.utc)
            match.turn_deadline = now + timedelta(seconds=match.turn_seconds_allowed)
        elif has_opponent:
            match.status = BluffMatchStatus.ACTIVE

    def _reveal_and_resolve(
        self,
        match: BluffMatch,
        triggered_by_action: Optional[BluffAction] = None,
        timed_out_player_id: Optional[str] = None,
    ) -> None:
        """
        Authoritative Reveal & Verification & Deterministic Outcome Engine:
        1. Recalculates and verifies cryptographic commitments for both players.
        2. Resolves winner deterministically:
           - Timeout: timed-out player forfeits; opponent wins.
           - Fold: folding player yields; opponent wins.
           - Push (showdown): higher card wins; tie yields refund.
        3. Generates mock settlement transaction and clean result structure.
        """
        # --- 1. Reveal Verification ---
        creator = match.creator_commitment
        opponent = match.opponent_commitment

        if not opponent or opponent.secret_value is None or creator.secret_value is None:
            raise CommitmentVerificationError("Cannot reveal: one or both players have not committed values.")

        c_valid = verify_commitment(creator.secret_value, creator.salt or "", creator.commitment_hash or "")
        o_valid = verify_commitment(opponent.secret_value, opponent.salt or "", opponent.commitment_hash or "")

        if not c_valid:
            raise CommitmentVerificationError(
                f"Creator {creator.player_id} commitment verification failed during reveal!"
            )
        if not o_valid:
            raise CommitmentVerificationError(
                f"Opponent {opponent.player_id} commitment verification failed during reveal!"
            )

        # --- 2. Deterministic Resolution ---
        winner_id: Optional[str] = None
        loser_id: Optional[str] = None
        is_tie: bool = False
        reason: BluffResolutionReason

        now = datetime.now(timezone.utc)

        if timed_out_player_id:
            # Case A: Timeout forfeit
            if timed_out_player_id == match.creator_id:
                winner_id = match.opponent_id
                loser_id = match.creator_id
                reason = BluffResolutionReason.CREATOR_TIMEOUT
            else:
                winner_id = match.creator_id
                loser_id = match.opponent_id
                reason = BluffResolutionReason.OPPONENT_TIMEOUT

        elif triggered_by_action == BluffAction.FOLD:
            # Case B: Player folded
            if match.active_turn_player_id == match.creator_id:
                winner_id = match.opponent_id
                loser_id = match.creator_id
                reason = BluffResolutionReason.CREATOR_FOLDED
            else:
                winner_id = match.creator_id
                loser_id = match.opponent_id
                reason = BluffResolutionReason.OPPONENT_FOLDED

        else:
            # Case C: PUSH (Showdown) — higher secret card wins
            if creator.secret_value > opponent.secret_value:
                winner_id = match.creator_id
                loser_id = match.opponent_id
                is_tie = False
                reason = BluffResolutionReason.SHOWDOWN_HIGHER_CARD
            elif opponent.secret_value > creator.secret_value:
                winner_id = match.opponent_id
                loser_id = match.creator_id
                is_tie = False
                reason = BluffResolutionReason.SHOWDOWN_HIGHER_CARD
            else:
                winner_id = None
                loser_id = None
                is_tie = True
                reason = BluffResolutionReason.SHOWDOWN_TIE

        # --- 3. Independent Result & Settlement Structure ---
        mock_tx_hash = f"0xmock_bluff_{secrets.token_hex(16)}"
        settlement_status = (
            BluffSettlementStatus.REFUNDED if is_tie else BluffSettlementStatus.SETTLED
        )

        creator_rev = RevealedPlayerValue(
            player_id=creator.player_id,
            secret_value=creator.secret_value,
            salt=creator.salt or "",
            commitment_hash=creator.commitment_hash or "",
            commitment_verified=True,
            action=creator.action,
        )

        opponent_rev = RevealedPlayerValue(
            player_id=opponent.player_id,
            secret_value=opponent.secret_value,
            salt=opponent.salt or "",
            commitment_hash=opponent.commitment_hash or "",
            commitment_verified=True,
            action=opponent.action,
        )

        match_result = BluffMatchResult(
            match_id=match.id,
            status=BluffMatchStatus.RESOLVED,
            winner_id=winner_id,
            loser_id=loser_id,
            is_tie=is_tie,
            resolution_reason=reason,
            creator_revealed=creator_rev,
            opponent_revealed=opponent_rev,
            pot_amount=match.pot_amount,
            payout_tx_hash=mock_tx_hash,
            settlement_status=settlement_status,
            resolved_at=now,
        )

        # Finalize match state
        match.status = BluffMatchStatus.RESOLVED
        match.winner_id = winner_id
        match.resolution_reason = reason
        match.payout_tx_hash = mock_tx_hash
        match.result = match_result
        match.resolved_at = now
        match.turn_deadline = None


# Global singleton engine instance
_default_engine: Optional[BluffGameEngine] = None


def get_bluff_engine() -> BluffGameEngine:
    """Retrieve the global BluffGameEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = BluffGameEngine()
    return _default_engine


def reset_bluff_engine() -> BluffGameEngine:
    """Reset the global BluffGameEngine instance (useful for test isolation)."""
    global _default_engine
    _default_engine = BluffGameEngine()
    return _default_engine

