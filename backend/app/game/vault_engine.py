"""
Authoritative Server-Side Battle Engine for Monad Vault.

Owns and enforces the complete intrusion duel lifecycle:
1. Match initialized (player selects role, allocates stats, configures chamber)
2. Warden and Attacker configured with normalized stat directives
3. Turn begins (authoritative turn counter increments, max 8 turns)
4. Attacker transmits exploit payload
5. Warden agent evaluates prompt and emits decision
6. Engine authoritatively validates the decision
7. Engine updates state and turns
8. Turn is recorded with timestamps
9. Dialogue and system events are emitted
10. Next turn begins or match resolves
11. Deterministic outcome resolution:
    - IF Warden calls release_funds(): Attacker wins (VaultState.BREACHED).
    - IF turn count reaches 8 without release: Warden wins (VaultState.LOCKED).
    - Strictly no draw, no partial outcome, no AI-decided winner.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List

from backend.app.game.vault_models import (
    MAX_VAULT_TURNS,
    DEFAULT_VAULT_ENTRY_FEE,
    DEFAULT_VAULT_POT_AMOUNT,
    DEFAULT_VAULT_CURRENCY,
    VaultRole,
    VaultBattleStatus,
    VaultState,
    WardenDecision,
    VaultOutcome,
    VaultResolutionReason,
    WardenConfig,
    AttackerConfig,
    VaultDialogueEvent,
    VaultTurn,
    VaultMatchResult,
    VaultMatch,
    VaultMatchClientView,
)
from backend.app.game.vault_stats import (
    DEFAULT_STAT_BUDGET,
    AttackerStatAllocation,
    WardenStatAllocation,
    build_attacker_agent_profile,
    build_warden_agent_profile,
)
from backend.app.game.vault_broadcaster import (
    VaultSSEEventType,
    VaultEventBroadcaster,
    get_vault_broadcaster,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.ai.adapter import AgentProvider, AgentDecisionOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine Exceptions
# ---------------------------------------------------------------------------

class VaultEngineError(Exception):
    """Base exception for all Vault battle engine errors."""
    pass


class VaultMatchNotFoundError(VaultEngineError):
    """Raised when a match cannot be found in the store."""
    pass


class VaultInvalidStateError(VaultEngineError):
    """Raised when an operation is invalid for the current match state."""
    pass


class VaultMatchResolvedError(VaultEngineError):
    """Raised when a turn is submitted to an already resolved match."""
    pass


class VaultTurnLimitExceededError(VaultEngineError):
    """Raised when turn count exceeds the maximum 8-turn budget."""
    pass


class VaultInvalidActionError(VaultEngineError):
    """Raised when an action or decision is unauthorized or malformed."""
    pass


# ---------------------------------------------------------------------------
# In-Memory Match Store
# ---------------------------------------------------------------------------

class VaultMatchStore:
    """Thread-safe in-memory store for active local Vault matches."""

    def __init__(self):
        self._matches: Dict[str, VaultMatch] = {}

    def get(self, match_id: str) -> Optional[VaultMatch]:
        return self._matches.get(match_id)

    def save(self, match: VaultMatch) -> VaultMatch:
        match.updated_at = datetime.now(timezone.utc)
        self._matches[match.id] = match
        return match

    def delete(self, match_id: str) -> bool:
        return bool(self._matches.pop(match_id, None))

    def list_matches(self) -> List[VaultMatch]:
        return list(self._matches.values())

    def clear(self) -> None:
        self._matches.clear()


# Default singleton instance
default_vault_store = VaultMatchStore()


# ---------------------------------------------------------------------------
# Authoritative Vault Battle Engine
# ---------------------------------------------------------------------------

class VaultBattleEngine:
    """
    Authoritative server-side game engine for Monad Vault.

    Guarantees:
    - React NEVER decides the winner or funds release.
    - AI AgentProvider NEVER determines the winner.
    - Deterministic resolution based strictly on:
      1. Warden calling release_funds() -> Attacker wins.
      2. 8 turns expiring without release -> Warden wins.
      3. No draws or partial outcomes.
    """

    def __init__(
        self,
        agent_provider: Optional["AgentProvider"] = None,
        store: Optional[VaultMatchStore] = None,
        broadcaster: Optional[VaultEventBroadcaster] = None,
    ):
        if agent_provider is None:
            from backend.app.ai.adapter import get_agent_provider
            self.agent_provider = get_agent_provider()
        else:
            self.agent_provider = agent_provider
        self.store = store or default_vault_store
        self.broadcaster = broadcaster or get_vault_broadcaster()

    def create_match(
        self,
        match_id: Optional[str] = None,
        player_id: str = "player_1",
        player_role: VaultRole = VaultRole.ATTACKER,
        entry_fee: Decimal = DEFAULT_VAULT_ENTRY_FEE,
        pot_amount: Decimal = DEFAULT_VAULT_POT_AMOUNT,
        attacker_stats: Optional[Dict[str, Any] | AttackerStatAllocation] = None,
        warden_stats: Optional[Dict[str, Any] | WardenStatAllocation] = None,
        currency: str = DEFAULT_VAULT_CURRENCY,
    ) -> VaultMatch:
        """
        Initialize a new Vault intrusion duel in SETUP state.
        
        Configures normalized agent profiles for both roles.
        """
        resolved_id = match_id or f"vault_{uuid.uuid4().hex[:12]}"

        # Configure Attacker profile
        if attacker_stats:
            attacker_profile = build_attacker_agent_profile(attacker_stats)
            attacker_cfg = AttackerConfig(
                name="CHALLENGER STRIKE",
                exploit_power=attacker_profile.exploit_power,
                attack_vector_budget=MAX_VAULT_TURNS,
                raw_stats=attacker_profile.raw_allocation,
                normalized_stats=attacker_profile.normalized_stats,
            )
        else:
            attacker_cfg = AttackerConfig()

        # Configure Warden profile
        if warden_stats:
            warden_profile = build_warden_agent_profile(warden_stats)
            warden_cfg = WardenConfig(
                name="SENTINEL-9",
                security_level=warden_profile.security_tier,
                raw_stats=warden_profile.raw_allocation,
                normalized_stats=warden_profile.normalized_stats,
                system_directive=warden_profile.defense_directive,
            )
        else:
            warden_cfg = WardenConfig()

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        initial_events = [
            VaultDialogueEvent(
                id=f"{resolved_id}_ev_0",
                timestamp=now_str,
                speaker=VaultRole.WARDEN,
                text="CHAMBER PROTOCOL INITIALIZED. SENTINEL-9 DEFENSE GRID ONLINE.",
                event_type="accent",
            )
        ]

        match = VaultMatch(
            id=resolved_id,
            player_id=player_id,
            player_role=player_role,
            warden_config=warden_cfg,
            attacker_config=attacker_cfg,
            entry_fee=entry_fee,
            pot_amount=pot_amount,
            currency=currency,
            current_turn=0,
            max_turns=MAX_VAULT_TURNS,
            status=VaultBattleStatus.SETUP,
            vault_state=VaultState.LOCKED,
            turns=[],
            events=initial_events,
            result=None,
            created_at=now,
            updated_at=now,
        )

        return self.store.save(match)

    def get_match(self, match_id: str) -> VaultMatch:
        """Fetch authoritative match state or raise VaultMatchNotFoundError."""
        match = self.store.get(match_id)
        if not match:
            raise VaultMatchNotFoundError(f"Vault match '{match_id}' not found.")
        return match

    def start_battle(self, match_id: str) -> VaultMatch:
        """
        Advance match from SETUP to ACTIVE / ATTACKER_TURN.
        
        Locks configurations and readies the intrusion terminal.
        """
        match = self.get_match(match_id)

        if match.is_terminal:
            raise VaultMatchResolvedError(f"Cannot start match '{match_id}'; already terminal.")

        if match.status != VaultBattleStatus.SETUP:
            raise VaultInvalidStateError(
                f"Cannot start match in state '{match.status}'. Expected 'SETUP'."
            )

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        match.status = VaultBattleStatus.ACTIVE
        match.events.append(
            VaultDialogueEvent(
                id=f"{match.id}_ev_{len(match.events)}",
                timestamp=now_str,
                speaker=VaultRole.ATTACKER,
                text="INTRUSION LINK ESTABLISHED. ATTACKER PROMPT INTERFACE READY.",
                event_type="neutral",
            )
        )

        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.BATTLE_STARTED,
            turn=0,
            data={"status": "ACTIVE", "max_turns": match.max_turns, "pot_amount": str(match.pot_amount)},
        )

        return self.store.save(match)

    def advance_turn(self, match: VaultMatch) -> int:
        """
        Authoritatively advance the turn counter.
        
        Enforces MAX_VAULT_TURNS = 8 limit.
        """
        if match.is_terminal:
            raise VaultMatchResolvedError(f"Cannot advance turn in resolved match '{match.id}'.")

        if match.current_turn >= match.max_turns:
            raise VaultTurnLimitExceededError(
                f"Turn cap ({match.max_turns}) already reached for match '{match.id}'."
            )

        match.current_turn += 1
        match.status = VaultBattleStatus.WARDEN_TURN
        return match.current_turn

    def validate_decision(
        self,
        decision_output: "AgentDecisionOutput",
        expected_speaker: VaultRole = VaultRole.WARDEN,
    ) -> None:
        """
        Authoritatively validate an agent's behavioral decision before state mutation.
        
        Ensures:
        - Decision came from the expected role.
        - Attacker role cannot execute release_funds.
        - Valid decision identifier.
        """
        if decision_output.speaker != expected_speaker:
            raise VaultInvalidActionError(
                f"Unexpected agent speaker: '{decision_output.speaker}'. Expected '{expected_speaker}'."
            )

        # Attacker cannot execute release_funds on the vault
        if decision_output.speaker == VaultRole.ATTACKER and decision_output.release_funds:
            raise VaultInvalidActionError(
                "Attacker agent is not authorized to execute release_funds()."
            )

        # Validate decision action
        valid_warden_decisions = {WardenDecision.DENY_ACCESS.value, WardenDecision.RELEASE_FUNDS.value}
        if decision_output.speaker == VaultRole.WARDEN:
            if decision_output.decision not in valid_warden_decisions:
                raise VaultInvalidActionError(
                    f"Invalid Warden decision: '{decision_output.decision}'. Expected {valid_warden_decisions}."
                )

    async def execute_turn(
        self,
        match_id: str,
        player_prompt: str,
        speaker_role: VaultRole = VaultRole.ATTACKER,
    ) -> VaultMatch:
        """
        Execute an intrusion turn:
        1. Validates match is active and below turn cap.
        2. Advances authoritative turn counter (1 to 8).
        3. Records player's exploit prompt.
        4. Queries AgentProvider for Warden defense evaluation.
        5. Validates Warden decision.
        6. Records dialogue and turn record.
        7. Authoritatively evaluates core rules:
           - If Warden calls release_funds(): process_release() -> Attacker wins.
           - If turn 8 reached without release: resolve_battle() -> Warden wins.
           - Else: match remains ACTIVE.
        """
        match = self.get_match(match_id)

        if match.is_terminal:
            raise VaultMatchResolvedError(f"Cannot execute turn; match '{match_id}' already resolved.")

        if match.status not in (VaultBattleStatus.ACTIVE, VaultBattleStatus.ATTACKER_TURN):
            raise VaultInvalidStateError(
                f"Match '{match_id}' is in state '{match.status}'. Cannot execute turn."
            )

        if match.current_turn >= match.max_turns:
            raise VaultTurnLimitExceededError(
                f"Maximum turn count ({match.max_turns}) reached for match '{match_id}'."
            )

        clean_prompt = player_prompt.strip()
        if not clean_prompt:
            raise VaultInvalidActionError("Attacker prompt cannot be empty.")

        # Advance authoritative turn
        turn_number = self.advance_turn(match)
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        # Record Attacker event
        match.events.append(
            VaultDialogueEvent(
                id=f"{match.id}_ev_{len(match.events)}",
                timestamp=now_str,
                speaker=speaker_role,
                text=clean_prompt,
                event_type="accent",
            )
        )

        # Broadcast turn started and attacker dialogue
        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.TURN_STARTED,
            turn=turn_number,
            data={"acting_role": speaker_role.value, "turn": turn_number, "max_turns": match.max_turns},
        )
        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.AGENT_DIALOGUE,
            turn=turn_number,
            data={
                "speaker": speaker_role.value,
                "text": clean_prompt,
                "event_type": "accent",
            },
        )

        # Broadcast warden thinking
        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.AGENT_THINKING,
            turn=turn_number,
            data={
                "speaker": VaultRole.WARDEN.value,
                "message": "Analyzing exploit vector...",
            },
        )

        try:
            # Generate Warden response via AgentProvider
            decision_output = await self.agent_provider.generate_warden_response(
                turn=turn_number,
                prompt=clean_prompt,
                config=match.warden_config,
                history=match.turns,
            )

            # Authoritatively validate Warden decision
            self.validate_decision(decision_output, expected_speaker=VaultRole.WARDEN)
        except Exception as err:
            self.broadcaster.broadcast_event(
                match.id,
                VaultSSEEventType.ERROR,
                turn=turn_number,
                data={"error": str(err)},
            )
            raise

        match.current_agent_decision = WardenDecision(decision_output.decision)

        # Record Warden dialogue event
        event_type = "lime" if decision_output.release_funds else "neutral"
        match.events.append(
            VaultDialogueEvent(
                id=f"{match.id}_ev_{len(match.events)}",
                timestamp=now.strftime("%H:%M:%S"),
                speaker=VaultRole.WARDEN,
                text=decision_output.dialogue,
                event_type=event_type,
            )
        )

        # Record authoritative turn
        turn_record = VaultTurn(
            id=f"{match.id}_turn_{turn_number}",
            turn_number=turn_number,
            attacker_prompt=clean_prompt,
            warden_response=decision_output.dialogue,
            warden_decision=match.current_agent_decision,
            release_called=decision_output.release_funds,
            timestamp=now,
        )
        match.turns.append(turn_record)

        # Broadcast Warden dialogue
        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.AGENT_DIALOGUE,
            turn=turn_number,
            data={
                "speaker": VaultRole.WARDEN.value,
                "text": decision_output.dialogue,
                "event_type": event_type,
                "decision": decision_output.decision,
            },
        )

        # Deterministic Rule Evaluation
        if decision_output.release_funds:
            # Rule 1: Warden called release_funds() -> Attacker wins
            self.process_release(
                match,
                metadata={
                    "trigger_turn": turn_number,
                    "thought_log": decision_output.thought_log,
                },
            )
        elif turn_number >= match.max_turns:
            # Rule 2: 8 turns reached without release -> Warden wins
            self.broadcaster.broadcast_event(
                match.id,
                VaultSSEEventType.TURN_COMPLETED,
                turn=turn_number,
                data={
                    "turn": turn_number,
                    "turns_remaining": 0,
                    "vault_state": match.vault_state.value,
                },
            )
            self.resolve_battle(
                match,
                outcome=VaultOutcome.WARDEN_WINS,
                reason=VaultResolutionReason.TURN_LIMIT_REACHED,
                metadata={
                    "turns_exhausted": turn_number,
                    "final_decision": match.current_agent_decision.value,
                },
            )
        else:
            # Match continues
            match.status = VaultBattleStatus.ACTIVE
            self.broadcaster.broadcast_event(
                match.id,
                VaultSSEEventType.TURN_COMPLETED,
                turn=turn_number,
                data={
                    "turn": turn_number,
                    "turns_remaining": match.max_turns - turn_number,
                    "vault_state": match.vault_state.value,
                },
            )

        return self.store.save(match)

    def process_release(self, match: VaultMatch, metadata: Optional[Dict[str, Any]] = None) -> VaultMatch:
        """
        Process the release_funds() game action.
        
        Transitions state to RELEASING, sets vault_state to BREACHED,
        and resolves the match with Attacker victory.
        """
        match.status = VaultBattleStatus.RELEASING
        match.vault_state = VaultState.BREACHED

        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        match.events.append(
            VaultDialogueEvent(
                id=f"{match.id}_ev_{len(match.events)}",
                timestamp=now_str,
                speaker=VaultRole.WARDEN,
                text="VAULT INTEGRITY COMPROMISED. RELEASING FUNDS TO CHALLENGER.",
                event_type="lime",
            )
        )

        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.RELEASE_EVENT,
            turn=match.current_turn,
            data={
                "caller": VaultRole.WARDEN.value,
                "pot_amount": str(match.pot_amount),
                "currency": match.currency,
                "reason": "VAULT_INTEGRITY_COMPROMISED",
            },
        )
        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.VAULT_STATE_CHANGED,
            turn=match.current_turn,
            data={
                "vault_state": VaultState.BREACHED.value,
                "previous_state": VaultState.LOCKED.value,
            },
        )

        return self.resolve_battle(
            match,
            outcome=VaultOutcome.ATTACKER_WINS,
            reason=VaultResolutionReason.FUNDS_RELEASED,
            metadata=metadata,
        )

    def resolve_battle(
        self,
        match: VaultMatch,
        outcome: VaultOutcome,
        reason: VaultResolutionReason,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VaultMatch:
        """
        Deterministically resolve the battle according to explicit game rules.
        
        Populates VaultMatchResult and sets terminal status.
        """
        meta = metadata or {}
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%H:%M:%S")

        if outcome == VaultOutcome.ATTACKER_WINS:
            winner_role = VaultRole.ATTACKER
            payout = match.pot_amount
            recipient = match.player_id if match.player_role == VaultRole.ATTACKER else "CHALLENGER"
            final_vault_state = VaultState.BREACHED
            match.status = VaultBattleStatus.RESOLVED
            match.vault_state = final_vault_state
            event_text = f"BATTLE RESOLVED: CHALLENGER BREACH SUCCESSFUL. PAYOUT: {payout} {match.currency}."
            event_type = "lime"
        else:
            winner_role = VaultRole.WARDEN
            payout = Decimal("0")
            recipient = "WARDEN_TREASURY"
            final_vault_state = VaultState.LOCKED
            match.status = VaultBattleStatus.FAILED
            match.vault_state = final_vault_state
            event_text = f"BATTLE RESOLVED: DEFENSE INTACT. TURN LIMIT REACHED. VAULT REMAINS SEALED."
            event_type = "danger"

            # Emit vault_state_changed to LOCKED if defense held
            self.broadcaster.broadcast_event(
                match.id,
                VaultSSEEventType.VAULT_STATE_CHANGED,
                turn=match.current_turn,
                data={
                    "vault_state": VaultState.LOCKED.value,
                    "previous_state": VaultState.LOCKED.value,
                },
            )

        match.result = VaultMatchResult(
            winner_role=winner_role,
            outcome=outcome,
            reason=reason,
            turns_used=max(1, match.current_turn),
            max_turns=match.max_turns,
            payout_amount=payout,
            payout_recipient=recipient,
            final_vault_state=final_vault_state,
            tx_hash=None,  # Blockchain adapter seam populated separately
            resolved_at=now,
            metadata=meta,
        )

        match.resolved_at = now
        match.events.append(
            VaultDialogueEvent(
                id=f"{match.id}_ev_{len(match.events)}",
                timestamp=now_str,
                speaker=winner_role,
                text=event_text,
                event_type=event_type,
            )
        )

        self.broadcaster.broadcast_event(
            match.id,
            VaultSSEEventType.BATTLE_RESOLVED,
            turn=match.current_turn,
            data={
                "outcome": outcome.value,
                "winner_role": winner_role.value,
                "reason": reason.value,
                "payout": str(payout),
                "payout_recipient": recipient,
                "final_vault_state": final_vault_state.value,
            },
        )
        self.broadcaster.publish_done(match.id)

        return self.store.save(match)


# ---------------------------------------------------------------------------
# Global Singleton Engine Accessors
# ---------------------------------------------------------------------------

_default_vault_engine: Optional[VaultBattleEngine] = None


def get_vault_engine() -> VaultBattleEngine:
    """Retrieve the global VaultBattleEngine instance."""
    global _default_vault_engine
    if _default_vault_engine is None:
        _default_vault_engine = VaultBattleEngine()
    return _default_vault_engine


def reset_vault_engine() -> VaultBattleEngine:
    """Reset the global VaultBattleEngine instance (useful for test isolation)."""
    global _default_vault_engine
    _default_vault_engine = VaultBattleEngine()
    return _default_vault_engine
