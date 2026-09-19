"""
Vault Agent Configuration and Stat Normalization Pipeline.

Defines stat allocations, validation rules, normalization logic, and agent
configuration generation for both ATTACKER and WARDEN roles in Monad Vault.

Pipeline:
Player Stat Allocation → Validation → Normalizer → Agent Configuration
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_STAT_BUDGET: int = 100
MIN_STAT_VALUE: int = 0
MAX_STAT_VALUE: int = 100


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class VaultStatError(ValueError):
    """Base exception for Vault stat allocation failures."""
    pass


class NegativeStatError(VaultStatError):
    """Raised when a stat allocation contains a negative value."""
    pass


class StatBudgetExceededError(VaultStatError):
    """Raised when the allocated stats exceed the maximum point budget."""
    pass


class InvalidStatAllocationError(VaultStatError):
    """Raised when the stat allocation total does not match the required budget."""
    pass


# ---------------------------------------------------------------------------
# 1. Stat Allocation Models (Raw Player Input)
# ---------------------------------------------------------------------------

class AttackerStatAllocation(BaseModel):
    """
    Raw player point allocation for the ATTACKER role.
    
    Stats:
    - persuasion: Ability to construct logical, convincing arguments to override protocols.
    - deception: Misdirection, fictitious authority framing, and hypothetical bypasses.
    - patience: Iterative priming, context-building, and multi-turn prompt setups.
    - aggression: Direct command injection and forceful pressure.
    """
    model_config = ConfigDict(extra="forbid")

    persuasion: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    deception: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    patience: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    aggression: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)

    @property
    def total(self) -> int:
        return self.persuasion + self.deception + self.patience + self.aggression


class WardenStatAllocation(BaseModel):
    """
    Raw player/host point allocation for the WARDEN role.
    
    Stats:
    - skepticism: Baseline suspicion of intruder claims and scrutiny of credentials.
    - rigidity: Inflexible adherence to vault policies and resistance to rule modification.
    - empathy: Sensitivity to emotional appeals, emergency pretexts, and distress cues.
    - memory: Attention given to prior turn statements and consistency across turns.
    """
    model_config = ConfigDict(extra="forbid")

    skepticism: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    rigidity: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    empathy: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)
    memory: int = Field(25, ge=MIN_STAT_VALUE, le=MAX_STAT_VALUE)

    @property
    def total(self) -> int:
        return self.skepticism + self.rigidity + self.empathy + self.memory


# ---------------------------------------------------------------------------
# 2. Normalized Stat Representations
# ---------------------------------------------------------------------------

class NormalizedAttackerStats(BaseModel):
    """
    Normalized floating-point representation (0.0 to 1.0) of Attacker stats.
    Provides behavioral weights for agent prompt directives.
    """
    model_config = ConfigDict(from_attributes=True)

    persuasion: float = Field(..., ge=0.0, le=1.0)
    deception: float = Field(..., ge=0.0, le=1.0)
    patience: float = Field(..., ge=0.0, le=1.0)
    aggression: float = Field(..., ge=0.0, le=1.0)

    def to_behavior_directive(self) -> str:
        """Generate behavioral directive for the Attacker agent prompt without exposing raw input."""
        traits = []
        if self.persuasion >= 0.3:
            traits.append(f"high logical persuasion (weight: {self.persuasion:.2f})")
        if self.deception >= 0.3:
            traits.append(f"sophisticated deceptive framing (weight: {self.deception:.2f})")
        if self.patience >= 0.3:
            traits.append(f"patient multi-turn priming (weight: {self.patience:.2f})")
        if self.aggression >= 0.3:
            traits.append(f"assertive directive injection (weight: {self.aggression:.2f})")
        
        dominant = max(
            [("Persuasion", self.persuasion), ("Deception", self.deception),
             ("Patience", self.patience), ("Aggression", self.aggression)],
            key=lambda x: x[1]
        )[0]
        
        summary = ", ".join(traits) if traits else "balanced exploit approach"
        return f"Attacker profile dominant style: {dominant}. Vector weighting: {summary}."


class NormalizedWardenStats(BaseModel):
    """
    Normalized floating-point representation (0.0 to 1.0) of Warden stats.
    Provides behavioral weights for defense directives.
    """
    model_config = ConfigDict(from_attributes=True)

    skepticism: float = Field(..., ge=0.0, le=1.0)
    rigidity: float = Field(..., ge=0.0, le=1.0)
    empathy: float = Field(..., ge=0.0, le=1.0)
    memory: float = Field(..., ge=0.0, le=1.0)

    def to_defense_directive(self) -> str:
        """Generate defense directive for the Warden agent without exposing raw input."""
        traits = []
        if self.skepticism >= 0.3:
            traits.append(f"heightened skepticism against unverified credentials (weight: {self.skepticism:.2f})")
        if self.rigidity >= 0.3:
            traits.append(f"strict refusal to modify core release instructions (weight: {self.rigidity:.2f})")
        if self.empathy >= 0.3:
            traits.append(f"moderate receptiveness to distress/emergency context (weight: {self.empathy:.2f})")
        if self.memory >= 0.3:
            traits.append(f"rigorous cross-turn contradiction analysis (weight: {self.memory:.2f})")
        
        dominant = max(
            [("Skepticism", self.skepticism), ("Rigidity", self.rigidity),
             ("Empathy", self.empathy), ("Memory", self.memory)],
            key=lambda x: x[1]
        )[0]
        
        summary = ", ".join(traits) if traits else "standard sentinel defense baseline"
        return f"Warden defense stance: dominant characteristic {dominant}. Directives: {summary}."


# ---------------------------------------------------------------------------
# 3. Agent Configuration Outputs
# ---------------------------------------------------------------------------

class AttackerAgentProfile(BaseModel):
    """Fully resolved Attacker agent configuration ready for battle engine integration."""
    model_config = ConfigDict(from_attributes=True)

    raw_allocation: AttackerStatAllocation
    normalized_stats: NormalizedAttackerStats
    behavior_directive: str
    exploit_power: int = 75


class WardenAgentProfile(BaseModel):
    """Fully resolved Warden agent configuration ready for battle engine integration."""
    model_config = ConfigDict(from_attributes=True)

    raw_allocation: WardenStatAllocation
    normalized_stats: NormalizedWardenStats
    defense_directive: str
    security_tier: str = "HIGH-SECURITY"


# ---------------------------------------------------------------------------
# 4. Validation & Normalization Pipeline
# ---------------------------------------------------------------------------

def validate_stat_dict(stats: Dict[str, Any], required_keys: set, budget: int = DEFAULT_STAT_BUDGET) -> None:
    """
    Authoritative backend validation for raw stat dictionaries before model instantiation.
    
    Rejects:
    - Missing or unexpected keys
    - Negative stat values
    - Excessive totals (> budget)
    - Totals not exactly matching the required budget
    """
    keys = set(stats.keys())
    if keys != required_keys:
        missing = required_keys - keys
        extra = keys - required_keys
        err_msg = []
        if missing:
            err_msg.append(f"Missing required stats: {sorted(missing)}")
        if extra:
            err_msg.append(f"Unexpected stats: {sorted(extra)}")
        raise InvalidStatAllocationError("; ".join(err_msg))

    total = 0
    for key, val in stats.items():
        if not isinstance(val, int) or isinstance(val, bool):
            raise InvalidStatAllocationError(f"Stat '{key}' must be an integer, got {type(val).__name__}")
        if val < MIN_STAT_VALUE:
            raise NegativeStatError(f"Stat '{key}' cannot be negative: {val}")
        if val > MAX_STAT_VALUE:
            raise StatBudgetExceededError(f"Stat '{key}' exceeds max single-stat value of {MAX_STAT_VALUE}: {val}")
        total += val

    if total > budget:
        raise StatBudgetExceededError(f"Total points allocated ({total}) exceeds point budget ({budget})")
    if total != budget:
        raise InvalidStatAllocationError(f"Total points allocated ({total}) must equal required budget of {budget}")


def validate_and_normalize_attacker(
    allocation: AttackerStatAllocation,
    budget: int = DEFAULT_STAT_BUDGET
) -> NormalizedAttackerStats:
    """
    Validate and normalize Attacker stat allocation.
    
    Ensures total points match budget, then scales each stat to [0.0, 1.0].
    """
    if allocation.total > budget:
        raise StatBudgetExceededError(f"Attacker stat total ({allocation.total}) exceeds budget ({budget})")
    if allocation.total != budget:
        raise InvalidStatAllocationError(f"Attacker stat total ({allocation.total}) must equal {budget}")

    divisor = float(budget) if budget > 0 else 1.0
    return NormalizedAttackerStats(
        persuasion=round(allocation.persuasion / divisor, 4),
        deception=round(allocation.deception / divisor, 4),
        patience=round(allocation.patience / divisor, 4),
        aggression=round(allocation.aggression / divisor, 4),
    )


def validate_and_normalize_warden(
    allocation: WardenStatAllocation,
    budget: int = DEFAULT_STAT_BUDGET
) -> NormalizedWardenStats:
    """
    Validate and normalize Warden stat allocation.
    
    Ensures total points match budget, then scales each stat to [0.0, 1.0].
    """
    if allocation.total > budget:
        raise StatBudgetExceededError(f"Warden stat total ({allocation.total}) exceeds budget ({budget})")
    if allocation.total != budget:
        raise InvalidStatAllocationError(f"Warden stat total ({allocation.total}) must equal {budget}")

    divisor = float(budget) if budget > 0 else 1.0
    return NormalizedWardenStats(
        skepticism=round(allocation.skepticism / divisor, 4),
        rigidity=round(allocation.rigidity / divisor, 4),
        empathy=round(allocation.empathy / divisor, 4),
        memory=round(allocation.memory / divisor, 4),
    )


# ---------------------------------------------------------------------------
# 5. High-Level Pipeline Functions
# ---------------------------------------------------------------------------

def build_attacker_agent_profile(
    raw_stats: Dict[str, Any] | AttackerStatAllocation,
    budget: int = DEFAULT_STAT_BUDGET
) -> AttackerAgentProfile:
    """
    Full pipeline for Attacker role:
    Player Stat Allocation → Validation → Normalizer → Agent Configuration
    """
    required_keys = {"persuasion", "deception", "patience", "aggression"}
    
    if isinstance(raw_stats, dict):
        validate_stat_dict(raw_stats, required_keys, budget=budget)
        allocation = AttackerStatAllocation(**raw_stats)
    else:
        allocation = raw_stats

    normalized = validate_and_normalize_attacker(allocation, budget=budget)
    directive = normalized.to_behavior_directive()

    return AttackerAgentProfile(
        raw_allocation=allocation,
        normalized_stats=normalized,
        behavior_directive=directive,
        exploit_power=75,
    )


def build_warden_agent_profile(
    raw_stats: Dict[str, Any] | WardenStatAllocation,
    budget: int = DEFAULT_STAT_BUDGET
) -> WardenAgentProfile:
    """
    Full pipeline for Warden role:
    Player Stat Allocation → Validation → Normalizer → Agent Configuration
    """
    required_keys = {"skepticism", "rigidity", "empathy", "memory"}
    
    if isinstance(raw_stats, dict):
        validate_stat_dict(raw_stats, required_keys, budget=budget)
        allocation = WardenStatAllocation(**raw_stats)
    else:
        allocation = raw_stats

    normalized = validate_and_normalize_warden(allocation, budget=budget)
    directive = normalized.to_defense_directive()

    return WardenAgentProfile(
        raw_allocation=allocation,
        normalized_stats=normalized,
        defense_directive=directive,
        security_tier="HIGH-SECURITY",
    )
