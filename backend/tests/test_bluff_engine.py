"""
Unit Tests for Authoritative Bluff or Bust Server-Side Game Engine.

Verifies:
- Valid match progression through complete lifecycle
- Invalid state transitions
- Invalid decisions
- Cryptographic reveal verification and tampering detection
- Deterministic outcome resolution (higher card wins, fold yields, tie refunds)
- Already-resolved and cancelled matches
- Invalid player action
- Unauthorized player action
- Client state sanitization (hidden secrets before reveal, revealed after resolve)
- Authoritative timeout resolution
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffResolutionReason,
    BluffSettlementStatus,
)
from backend.app.game.bluff_crypto import create_commitment, generate_salt
from backend.app.game.bluff_engine import (
    BluffGameEngine,
    BluffMatchStore,
    MatchNotFoundError,
    InvalidStateTransitionError,
    UnauthorizedPlayerError,
    InvalidDecisionError,
    InvalidSecretValueError,
    CommitmentVerificationError,
    MatchAlreadyResolvedError,
)


@pytest.fixture
def engine() -> BluffGameEngine:
    """Fixture providing a fresh isolated BluffGameEngine instance for each test."""
    store = BluffMatchStore()
    return BluffGameEngine(store=store)


class TestBluffEngineValidProgression:
    """Tests covering valid progression through all phases of match lifecycle."""

    def test_full_push_duel_progression(self, engine: BluffGameEngine):
        """
        1. Match created with creator secret
        2. Opponent joins with secret
        3. Match enters DECISION phase
        4. Opponent chooses PUSH
        5. Reveal verifies commitments
        6. Server deterministically resolves match
        7. Result is clean and independent
        """
        # Step 1: Create match
        match = engine.create_match(
            creator_id="0xalice",
            stake_amount=Decimal("5.0"),
            secret_value=8,
            turn_seconds=15,
        )
        assert match.status == BluffMatchStatus.WAITING
        assert match.creator_id == "0xalice"
        assert match.opponent_id is None
        assert match.creator_commitment.has_committed is True
        assert match.creator_commitment.secret_value == 8
        assert match.creator_commitment.commitment_hash is not None

        # Verify client view before opponent joins
        alice_view = engine.get_client_view(match.id, viewer_id="0xalice")
        assert alice_view.creator.secret_value == 8
        assert alice_view.opponent is None
        assert alice_view.can_act is False

        # Step 2: Opponent joins with secret
        match = engine.join_match(
            match_id=match.id,
            opponent_id="0xbob",
            secret_value=5,
        )
        assert match.status == BluffMatchStatus.DECISION
        assert match.opponent_id == "0xbob"
        assert match.opponent_commitment.has_committed is True
        assert match.active_turn_player_id == "0xbob"
        assert match.seconds_remaining() > 0

        # Verify client view in DECISION phase: secrets are hidden across opponents
        alice_view = engine.get_client_view(match.id, viewer_id="0xalice")
        assert alice_view.creator.secret_value == 8
        assert alice_view.opponent.secret_value is None  # Alice cannot see Bob's secret!
        assert alice_view.can_act is False

        bob_view = engine.get_client_view(match.id, viewer_id="0xbob")
        assert bob_view.creator.secret_value is None  # Bob cannot see Alice's secret!
        assert bob_view.opponent.secret_value == 5
        assert bob_view.can_act is True

        # Step 3: Active player (Bob) chooses PUSH (Showdown)
        resolved = engine.submit_action(
            match_id=match.id,
            player_id="0xbob",
            action=BluffAction.PUSH,
        )

        # Step 4: Verification and deterministic resolution (8 > 5 -> Alice wins)
        assert resolved.status == BluffMatchStatus.RESOLVED
        assert resolved.winner_id == "0xalice"
        assert resolved.resolution_reason == BluffResolutionReason.SHOWDOWN_HIGHER_CARD
        assert resolved.payout_tx_hash is not None
        assert resolved.result is not None

        # Result structure verification
        result = resolved.result
        assert result.winner_id == "0xalice"
        assert result.loser_id == "0xbob"
        assert result.is_tie is False
        assert result.creator_revealed.secret_value == 8
        assert result.creator_revealed.commitment_verified is True
        assert result.opponent_revealed.secret_value == 5
        assert result.opponent_revealed.commitment_verified is True
        assert result.opponent_revealed.action == BluffAction.PUSH
        assert result.settlement_status == BluffSettlementStatus.SETTLED

        # Resolved client view: both secrets are now revealed to everyone for auditing
        public_view = engine.get_client_view(match.id, viewer_id="0xspectator")
        assert public_view.status == BluffMatchStatus.RESOLVED
        assert public_view.creator.secret_value == 8
        assert public_view.opponent.secret_value == 5
        assert public_view.winner_id == "0xalice"
        assert public_view.result is not None

    def test_delayed_commit_secret_progression(self, engine: BluffGameEngine):
        """Match created uncommitted -> joined uncommitted -> committed sequentially -> enters decision."""
        # Create uncommitted
        match = engine.create_match(creator_id="0xalice", stake_amount=Decimal("2.5"))
        assert match.creator_commitment.has_committed is False
        assert match.status == BluffMatchStatus.WAITING

        # Join uncommitted
        match = engine.join_match(match.id, opponent_id="0xbob")
        assert match.opponent_commitment.has_committed is False
        assert match.status == BluffMatchStatus.ACTIVE

        # Creator commits
        match = engine.commit_secret(match.id, player_id="0xalice", secret_value=4)
        assert match.creator_commitment.has_committed is True
        assert match.status == BluffMatchStatus.ACTIVE  # Waiting for bob

        # Bob commits -> enters DECISION
        match = engine.commit_secret(match.id, player_id="0xbob", secret_value=7)
        assert match.opponent_commitment.has_committed is True
        assert match.status == BluffMatchStatus.DECISION
        assert match.active_turn_player_id == "0xbob"

    def test_fold_decision_yields_uncontested_victory(self, engine: BluffGameEngine):
        """When the active player chooses FOLD, the opponent wins immediately without secret comparison."""
        match = engine.create_match(creator_id="0xalice", secret_value=2)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=10)

        # Bob has 10 (which is higher than Alice's 2), but Bob chooses FOLD
        resolved = engine.submit_action(match.id, player_id="0xbob", action=BluffAction.FOLD)

        assert resolved.status == BluffMatchStatus.RESOLVED
        assert resolved.winner_id == "0xalice"  # Alice wins because Bob folded!
        assert resolved.resolution_reason == BluffResolutionReason.OPPONENT_FOLDED
        assert resolved.result.loser_id == "0xbob"
        assert resolved.result.creator_revealed.secret_value == 2
        assert resolved.result.opponent_revealed.secret_value == 10


class TestBluffEngineInvalidTransitions:
    """Tests covering invalid state transitions."""

    def test_cannot_join_non_waiting_match(self, engine: BluffGameEngine):
        """Opponent cannot join match already in DECISION or RESOLVED state."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=5)

        # Match is now in DECISION
        with pytest.raises(InvalidStateTransitionError, match="status is DECISION, expected WAITING"):
            engine.join_match(match.id, opponent_id="0xcharlie", secret_value=6)

    def test_cannot_commit_in_decision_or_resolved_state(self, engine: BluffGameEngine):
        """Cannot commit secret value once match is in DECISION."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(InvalidStateTransitionError, match="Cannot commit secret in state DECISION"):
            engine.commit_secret(match.id, player_id="0xalice", secret_value=7)

    def test_cannot_act_when_match_is_waiting(self, engine: BluffGameEngine):
        """Player cannot submit action before opponent has joined."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)

        with pytest.raises(InvalidStateTransitionError, match="must be in DECISION"):
            engine.submit_action(match.id, player_id="0xalice", action=BluffAction.PUSH)

    def test_cannot_cancel_after_opponent_joined(self, engine: BluffGameEngine):
        """Creator cannot cancel match after opponent has entered."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(InvalidStateTransitionError, match="opponent has already joined"):
            engine.cancel_match(match.id, player_id="0xalice")

    def test_cannot_timeout_unexpired_match(self, engine: BluffGameEngine):
        """handle_timeout raises error if countdown deadline is still active."""
        match = engine.create_match(creator_id="0xalice", secret_value=5, turn_seconds=20)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(InvalidStateTransitionError, match="Turn deadline has not elapsed yet"):
            engine.handle_timeout(match.id)


class TestBluffEngineInvalidDecisions:
    """Tests covering invalid or unsupported decision payloads."""

    def test_invalid_decision_string_rejected(self, engine: BluffGameEngine):
        """Submitting an invalid action string raises InvalidDecisionError."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(InvalidDecisionError, match="Invalid bluff action 'RAISE'"):
            engine.submit_action(match.id, player_id="0xbob", action="RAISE")

    def test_none_or_unsupported_type_action_rejected(self, engine: BluffGameEngine):
        """Submitting non-string / non-BluffAction decision raises InvalidDecisionError."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(InvalidDecisionError):
            engine.submit_action(match.id, player_id="0xbob", action=123)  # type: ignore


class TestBluffEngineRevealVerification:
    """Tests covering cryptographic commitment recalculation and tampering detection."""

    def test_tampered_secret_value_fails_reveal(self, engine: BluffGameEngine):
        """If a player's secret card is modified in storage, reveal verification fails."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        # Maliciously modify Alice's secret value in the domain object
        match.creator_commitment.secret_value = 9

        with pytest.raises(CommitmentVerificationError, match="Creator 0xalice commitment verification failed"):
            engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)

    def test_tampered_salt_fails_reveal(self, engine: BluffGameEngine):
        """If salt is swapped or modified, reveal verification fails."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        # Maliciously modify Bob's salt
        match.opponent_commitment.salt = "fake_salt_modified_maliciously"

        with pytest.raises(CommitmentVerificationError, match="Opponent 0xbob commitment verification failed"):
            engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)

    def test_tampered_commitment_hash_fails_reveal(self, engine: BluffGameEngine):
        """If commitment hash in storage does not match recalculated sha256(secret:salt), reveal fails."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        # Maliciously tamper with stored hash
        match.creator_commitment.commitment_hash = "deadbeef" * 8

        with pytest.raises(CommitmentVerificationError):
            engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)


class TestBluffEngineDeterministicResolution:
    """Tests covering exact, deterministic resolution rules."""

    def test_higher_card_wins_creator(self, engine: BluffGameEngine):
        """Creator: 9 vs Opponent: 4 -> Creator wins."""
        match = engine.create_match(creator_id="0xalice", secret_value=9)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=4)

        resolved = engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)
        assert resolved.winner_id == "0xalice"
        assert resolved.resolution_reason == BluffResolutionReason.SHOWDOWN_HIGHER_CARD
        assert resolved.result.is_tie is False

    def test_higher_card_wins_opponent(self, engine: BluffGameEngine):
        """Creator: 3 vs Opponent: 8 -> Opponent wins."""
        match = engine.create_match(creator_id="0xalice", secret_value=3)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=8)

        resolved = engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)
        assert resolved.winner_id == "0xbob"
        assert resolved.resolution_reason == BluffResolutionReason.SHOWDOWN_HIGHER_CARD
        assert resolved.result.is_tie is False

    def test_identical_cards_result_in_tie(self, engine: BluffGameEngine):
        """Creator: 7 vs Opponent: 7 -> Tie refund."""
        match = engine.create_match(creator_id="0xalice", secret_value=7)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=7)

        resolved = engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)
        assert resolved.winner_id is None
        assert resolved.resolution_reason == BluffResolutionReason.SHOWDOWN_TIE
        assert resolved.result.is_tie is True
        assert resolved.result.winner_id is None
        assert resolved.result.loser_id is None
        assert resolved.result.settlement_status == BluffSettlementStatus.REFUNDED

    def test_authoritative_timeout_resolution(self, engine: BluffGameEngine):
        """When turn countdown elapses, handle_timeout resolves against the active player."""
        match = engine.create_match(creator_id="0xalice", secret_value=6)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=3)

        # Bob holds the active turn. Simulate time elapse past deadline:
        match.turn_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)

        resolved = engine.handle_timeout(match.id)
        assert resolved.status == BluffMatchStatus.RESOLVED
        assert resolved.winner_id == "0xalice"  # Alice wins because Bob timed out!
        assert resolved.resolution_reason == BluffResolutionReason.OPPONENT_TIMEOUT
        assert resolved.result.loser_id == "0xbob"


class TestBluffEngineAlreadyResolvedMatch:
    """Tests operations on matches that have already completed."""

    def test_cannot_act_on_resolved_match(self, engine: BluffGameEngine):
        """Submitting action on already resolved match raises MatchAlreadyResolvedError."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)
        engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)

        with pytest.raises(MatchAlreadyResolvedError, match="is already RESOLVED"):
            engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)

    def test_cannot_join_or_cancel_resolved_match(self, engine: BluffGameEngine):
        """Cannot join or cancel an already resolved match."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)
        engine.submit_action(match.id, player_id="0xbob", action=BluffAction.PUSH)

        with pytest.raises(MatchAlreadyResolvedError):
            engine.join_match(match.id, opponent_id="0xcharlie", secret_value=5)

        with pytest.raises(MatchAlreadyResolvedError):
            engine.cancel_match(match.id, player_id="0xalice")

    def test_cannot_act_on_cancelled_match(self, engine: BluffGameEngine):
        """Cannot act or commit on a cancelled match."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.cancel_match(match.id, player_id="0xalice")
        assert match.status == BluffMatchStatus.CANCELLED

        with pytest.raises(MatchAlreadyResolvedError, match="is already CANCELLED"):
            engine.join_match(match.id, opponent_id="0xbob", secret_value=5)


class TestBluffEngineInvalidAndUnauthorizedPlayerActions:
    """Tests covering invalid player actions and unauthorized access."""

    def test_creator_cannot_join_own_match_as_opponent(self, engine: BluffGameEngine):
        """Host cannot duel themselves."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)

        with pytest.raises(UnauthorizedPlayerError, match="Creator cannot join their own match"):
            engine.join_match(match.id, opponent_id="0xalice", secret_value=6)

    def test_non_participant_cannot_submit_action(self, engine: BluffGameEngine):
        """A random wallet cannot submit action in someone else's duel."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        with pytest.raises(UnauthorizedPlayerError, match="Player 0xeve is not an authorized participant"):
            engine.submit_action(match.id, player_id="0xeve", action=BluffAction.PUSH)

    def test_inactive_player_cannot_act_out_of_turn(self, engine: BluffGameEngine):
        """Alice cannot submit action when it is Bob's turn."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)
        engine.join_match(match.id, opponent_id="0xbob", secret_value=6)

        assert match.active_turn_player_id == "0xbob"

        with pytest.raises(UnauthorizedPlayerError, match="It is not player 0xalice's turn to act"):
            engine.submit_action(match.id, player_id="0xalice", action=BluffAction.PUSH)

    def test_non_creator_cannot_cancel_match(self, engine: BluffGameEngine):
        """Only the creator can cancel an open match."""
        match = engine.create_match(creator_id="0xalice", secret_value=5)

        with pytest.raises(UnauthorizedPlayerError, match="Only the match creator can cancel"):
            engine.cancel_match(match.id, player_id="0xbob")

    def test_invalid_secret_card_values_rejected(self, engine: BluffGameEngine):
        """Secret card values < 1 or > 10 raise InvalidSecretValueError."""
        with pytest.raises(InvalidSecretValueError):
            engine.create_match(creator_id="0xalice", secret_value=0)

        with pytest.raises(InvalidSecretValueError):
            engine.create_match(creator_id="0xalice", secret_value=11)

        match = engine.create_match(creator_id="0xalice", secret_value=5)
        with pytest.raises(InvalidSecretValueError):
            engine.join_match(match.id, opponent_id="0xbob", secret_value=-3)

    def test_match_not_found_raises_cleanly(self, engine: BluffGameEngine):
        """Querying a non-existent match raises MatchNotFoundError."""
        with pytest.raises(MatchNotFoundError, match="was not found"):
            engine.get_match("bluff_non_existent_999")
