"""Authoritative Game Engine Seam.

Backend owns authoritative game state and resolution.
React UI remains strictly presentation-focused.
"""
from typing import Dict, Any


class GameEngineSeam:
    """Seam for game mechanics and authoritative round resolutions."""

    @staticmethod
    def resolve_bluff_round(creator_secret: int, opponent_secret: int, caller: str) -> Dict[str, Any]:
        """Authoritative bluff resolution using BluffGameEngine."""
        from backend.app.game.bluff_engine import BluffGameEngine
        from backend.app.game.bluff_models import BluffAction

        engine = BluffGameEngine()
        match = engine.create_match(creator_id="creator", secret_value=creator_secret)
        engine.join_match(match.id, opponent_id="opponent", secret_value=opponent_secret)
        resolved = engine.submit_action(match.id, player_id="opponent", action=BluffAction.PUSH)
        return resolved.model_dump()

    @staticmethod
    def evaluate_vault_turn(turn: int, prompt: str) -> Dict[str, Any]:
        """Authoritative vault breach evaluation."""
        pass
