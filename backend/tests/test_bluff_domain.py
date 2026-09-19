from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from pydantic import ValidationError

from backend.app.game.bluff_models import (
    BluffMatchStatus,
    BluffAction,
    BluffResolutionReason,
    PlayerCommitment,
    BluffMatch,
)


class TestBluffDomainModel:
    def test_status_and_action_enums(self):
        """Verify explicit lifecycle state and action enums."""
        assert BluffMatchStatus.WAITING == "WAITING"
        assert BluffMatchStatus.ACTIVE == "ACTIVE"
        assert BluffMatchStatus.DECISION == "DECISION"
        assert BluffMatchStatus.REVEALING == "REVEALING"
        assert BluffMatchStatus.RESOLVED == "RESOLVED"
        assert BluffMatchStatus.CANCELLED == "CANCELLED"

        assert BluffAction.PUSH == "PUSH"
        assert BluffAction.FOLD == "FOLD"

        assert BluffResolutionReason.SHOWDOWN_HIGHER_CARD == "SHOWDOWN_HIGHER_CARD"
        assert BluffResolutionReason.SHOWDOWN_TIE == "SHOWDOWN_TIE"
        assert BluffResolutionReason.CREATOR_FOLDED == "CREATOR_FOLDED"
        assert BluffResolutionReason.OPPONENT_FOLDED == "OPPONENT_FOLDED"

    def test_player_commitment_validation(self):
        """Secret card values must be bounded between 1 and 10."""
        # Valid commitment
        p = PlayerCommitment(player_id="player_1", secret_value=7, has_committed=True)
        assert p.secret_value == 7
        assert p.has_committed is True

        # Out-of-bounds: secret_value < 1
        with pytest.raises(ValidationError):
            PlayerCommitment(player_id="player_1", secret_value=0)

        # Out-of-bounds: secret_value > 10
        with pytest.raises(ValidationError):
            PlayerCommitment(player_id="player_1", secret_value=11)

    def test_match_creation_state(self):
        """Verify initial match state when created by host."""
        creator_comm = PlayerCommitment(
            player_id="0xcreator",
            secret_value=8,
            has_committed=True,
            committed_at=datetime.now(timezone.utc),
        )
        match = BluffMatch(
            id="bluff_1001",
            creator_id="0xcreator",
            stake_amount=Decimal("5.0"),
            pot_amount=Decimal("10.0"),
            status=BluffMatchStatus.WAITING,
            creator_commitment=creator_comm,
        )

        assert match.id == "bluff_1001"
        assert match.creator_id == "0xcreator"
        assert match.opponent_id is None
        assert match.status == BluffMatchStatus.WAITING
        assert match.stake_amount == Decimal("5.0")
        assert match.pot_amount == Decimal("10.0")

    def test_client_view_sanitization_hides_opponent_secret(self):
        """Server must strictly mask opponent's secret value until RESOLVED."""
        creator_comm = PlayerCommitment(
            player_id="0xcreator",
            secret_value=9,
            has_committed=True,
        )
        opponent_comm = PlayerCommitment(
            player_id="0xopponent",
            secret_value=4,
            has_committed=True,
        )
        match = BluffMatch(
            id="bluff_1002",
            creator_id="0xcreator",
            opponent_id="0xopponent",
            stake_amount=Decimal("10.0"),
            pot_amount=Decimal("20.0"),
            status=BluffMatchStatus.DECISION,
            creator_commitment=creator_comm,
            opponent_commitment=opponent_comm,
            active_turn_player_id="0xcreator",
            turn_deadline=datetime.now(timezone.utc) + timedelta(seconds=15),
        )

        # 1. Creator view: sees own secret (9), opponent secret is None
        creator_view = match.to_client_view(viewer_id="0xcreator")
        assert creator_view.creator.secret_value == 9
        assert creator_view.opponent.secret_value is None
        assert creator_view.is_creator is True
        assert creator_view.can_act is True
        assert creator_view.seconds_remaining > 0

        # 2. Opponent view: sees own secret (4), creator secret is None
        opponent_view = match.to_client_view(viewer_id="0xopponent")
        assert opponent_view.creator.secret_value is None
        assert opponent_view.opponent.secret_value == 4
        assert opponent_view.is_creator is False
        assert opponent_view.can_act is False

        # 3. Spectator view: neither secret is visible
        spectator_view = match.to_client_view(viewer_id="0xstranger")
        assert spectator_view.creator.secret_value is None
        assert spectator_view.opponent.secret_value is None
        assert spectator_view.can_act is False

        # 4. Resolved match: both secrets revealed to everyone
        match.status = BluffMatchStatus.RESOLVED
        match.winner_id = "0xcreator"
        match.resolution_reason = BluffResolutionReason.SHOWDOWN_HIGHER_CARD

        resolved_view = match.to_client_view(viewer_id="0xstranger")
        assert resolved_view.creator.secret_value == 9
        assert resolved_view.opponent.secret_value == 4
        assert resolved_view.winner_id == "0xcreator"
        assert resolved_view.resolution_reason == BluffResolutionReason.SHOWDOWN_HIGHER_CARD

    def test_authoritative_countdown_and_expiration(self):
        """Authoritative turn expiration must be calculated server-side."""
        now = datetime.now(timezone.utc)
        creator_comm = PlayerCommitment(player_id="0x1", secret_value=5, has_committed=True)
        match = BluffMatch(
            id="bluff_1003",
            creator_id="0x1",
            status=BluffMatchStatus.DECISION,
            creator_commitment=creator_comm,
            active_turn_player_id="0x1",
            turn_deadline=now + timedelta(seconds=10),
        )

        assert match.is_expired() is False
        assert 8 <= match.seconds_remaining() <= 10

        # Past deadline
        match.turn_deadline = now - timedelta(seconds=1)
        assert match.is_expired() is True
        assert match.seconds_remaining() == 0

    def test_state_restoration_on_reconnect(self):
        """A client reconnecting / refreshing receives full deterministic state."""
        creator_comm = PlayerCommitment(player_id="0xplayerA", secret_value=3, has_committed=True)
        match = BluffMatch(
            id="bluff_resume_99",
            creator_id="0xplayerA",
            status=BluffMatchStatus.WAITING,
            creator_commitment=creator_comm,
        )

        view = match.to_client_view(viewer_id="0xplayerA")
        assert view.id == "bluff_resume_99"
        assert view.status == BluffMatchStatus.WAITING
        assert view.creator.secret_value == 3
        assert view.opponent is None
