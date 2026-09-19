import pytest
from decimal import Decimal
from backend.app.game.bluff_crypto import (
    generate_salt,
    generate_secret_value,
    create_commitment,
    verify_commitment,
    create_secret_commitment,
)
from backend.app.game.bluff_models import (
    BluffMatch,
    BluffMatchStatus,
    PlayerCommitment,
)


class TestBluffCommitmentReveal:
    def test_same_secret_and_salt_produces_same_commitment(self):
        """Determinism check: same secret + salt must generate the exact same hash."""
        secret = 7
        salt = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

        hash1 = create_commitment(secret, salt)
        hash2 = create_commitment(secret, salt)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex string

    def test_valid_reveal_verifies(self):
        """A legitimate reveal matching the original commitment must pass verification."""
        secret, salt, commitment = create_secret_commitment(secret=8)
        assert verify_commitment(secret, salt, commitment) is True

    def test_modified_secret_fails_verification(self):
        """Attempting to reveal a different secret than committed must be rejected."""
        committed_secret, salt, commitment = create_secret_commitment(secret=6)
        tampered_secret = 7

        assert verify_commitment(tampered_secret, salt, commitment) is False

    def test_modified_salt_fails_verification(self):
        """Attempting to verify with a modified salt must be rejected."""
        secret, committed_salt, commitment = create_secret_commitment(secret=5)
        tampered_salt = committed_salt[:-2] + "ff"

        assert verify_commitment(secret, tampered_salt, commitment) is False

    def test_modified_commitment_fails_verification(self):
        """Attempting to verify against a corrupted or forged commitment hash must fail."""
        secret, salt, commitment = create_secret_commitment(secret=4)
        tampered_commitment = "0" * 64

        assert verify_commitment(secret, salt, tampered_commitment) is False

    def test_hidden_secret_is_not_returned_before_reveal(self):
        """
        API security check:
        The opponent's secret value and salt must NEVER be exposed in client views
        before the match reaches the RESOLVED state.
        """
        creator_sec, creator_salt, creator_hash = create_secret_commitment(secret=9)
        opponent_sec, opponent_salt, opponent_hash = create_secret_commitment(secret=3)

        match = BluffMatch(
            id="bluff_sec_test",
            creator_id="0xcreator_wallet",
            opponent_id="0xopponent_wallet",
            stake_amount=Decimal("5.0"),
            pot_amount=Decimal("10.0"),
            status=BluffMatchStatus.DECISION,
            creator_commitment=PlayerCommitment(
                player_id="0xcreator_wallet",
                secret_value=creator_sec,
                salt=creator_salt,
                commitment_hash=creator_hash,
                has_committed=True,
            ),
            opponent_commitment=PlayerCommitment(
                player_id="0xopponent_wallet",
                secret_value=opponent_sec,
                salt=opponent_salt,
                commitment_hash=opponent_hash,
                has_committed=True,
            ),
        )

        # 1. Creator viewing the match
        creator_view = match.to_client_view(viewer_id="0xcreator_wallet")
        assert creator_view.creator.secret_value == 9
        assert creator_view.creator.salt == creator_salt
        assert creator_view.creator.commitment_hash == creator_hash
        # Opponent secret & salt are strictly None
        assert creator_view.opponent.secret_value is None
        assert creator_view.opponent.salt is None
        # But opponent commitment hash is public for later verification
        assert creator_view.opponent.commitment_hash == opponent_hash

        # 2. Opponent viewing the match
        opponent_view = match.to_client_view(viewer_id="0xopponent_wallet")
        assert opponent_view.opponent.secret_value == 3
        assert opponent_view.opponent.salt == opponent_salt
        # Creator secret & salt are strictly None
        assert opponent_view.creator.secret_value is None
        assert opponent_view.creator.salt is None
        assert opponent_view.creator.commitment_hash == creator_hash

        # 3. Third-party spectator viewing the match
        spectator_view = match.to_client_view(viewer_id="0xspectator")
        assert spectator_view.creator.secret_value is None
        assert spectator_view.creator.salt is None
        assert spectator_view.opponent.secret_value is None
        assert spectator_view.opponent.salt is None

        # 4. Once match is RESOLVED, secrets and salts are revealed to all
        match.status = BluffMatchStatus.RESOLVED
        resolved_view = match.to_client_view(viewer_id="0xspectator")
        assert resolved_view.creator.secret_value == 9
        assert resolved_view.creator.salt == creator_salt
        assert resolved_view.opponent.secret_value == 3
        assert resolved_view.opponent.salt == opponent_salt

        # Both revealed cards can now be verified by anyone
        assert verify_commitment(
            resolved_view.creator.secret_value,
            resolved_view.creator.salt,
            resolved_view.creator.commitment_hash,
        ) is True
        assert verify_commitment(
            resolved_view.opponent.secret_value,
            resolved_view.opponent.salt,
            resolved_view.opponent.commitment_hash,
        ) is True

    def test_secret_generation_bounds(self):
        """Secret generator generates values within isolated bounds (1 to 10)."""
        values = {generate_secret_value() for _ in range(100)}
        assert all(1 <= v <= 10 for v in values)
        assert len(values) > 1

    def test_salt_uniqueness(self):
        """Generated salts must be cryptographically non-predictable and unique."""
        salts = [generate_salt() for _ in range(50)]
        assert len(set(salts)) == 50
        assert all(len(s) == 64 for s in salts)

    def test_bluff_match_integrity_check(self):
        """BluffMatch.verify_commitment_integrity must validate stored commitments."""
        sec, salt, c_hash = create_secret_commitment(secret=10)
        match = BluffMatch(
            id="m1",
            creator_id="c1",
            creator_commitment=PlayerCommitment(
                player_id="c1",
                secret_value=sec,
                salt=salt,
                commitment_hash=c_hash,
                has_committed=True,
            ),
        )
        assert match.verify_commitment_integrity("c1") is True

        # Tamper with stored secret
        match.creator_commitment.secret_value = 9
        assert match.verify_commitment_integrity("c1") is False
