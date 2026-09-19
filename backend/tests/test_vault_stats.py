"""
Unit tests for Vault agent configuration and stat normalization pipeline.

Tests:
- Valid allocation for both roles
- Invalid allocation (missing keys, extra keys, non-integer types)
- Negative values rejection (NegativeStatError)
- Excessive allocation rejection (StatBudgetExceededError)
- Normalization (values strictly in [0.0, 1.0] summing to 1.0)
- Both roles: ATTACKER and WARDEN
- Pipeline: Player Stat Allocation → Validation → Normalizer → Agent Configuration
"""

import pytest
from pydantic import ValidationError

from backend.app.game.vault_stats import (
    DEFAULT_STAT_BUDGET,
    MIN_STAT_VALUE,
    MAX_STAT_VALUE,
    NegativeStatError,
    StatBudgetExceededError,
    InvalidStatAllocationError,
    AttackerStatAllocation,
    WardenStatAllocation,
    NormalizedAttackerStats,
    NormalizedWardenStats,
    AttackerAgentProfile,
    WardenAgentProfile,
    validate_stat_dict,
    validate_and_normalize_attacker,
    validate_and_normalize_warden,
    build_attacker_agent_profile,
    build_warden_agent_profile,
)


class TestVaultStatsPipeline:
    """Test suite for Vault agent configuration and stat normalization."""

    # -----------------------------------------------------------------------
    # ATTACKER Role Tests
    # -----------------------------------------------------------------------

    def test_valid_attacker_allocation(self):
        """Test valid 100-point allocation for Attacker."""
        raw = {
            "persuasion": 40,
            "deception": 30,
            "patience": 20,
            "aggression": 10,
        }
        profile = build_attacker_agent_profile(raw)

        assert isinstance(profile, AttackerAgentProfile)
        assert profile.raw_allocation.persuasion == 40
        assert profile.raw_allocation.deception == 30
        assert profile.raw_allocation.patience == 20
        assert profile.raw_allocation.aggression == 10
        assert profile.raw_allocation.total == 100

        # Verify normalization to floats [0.0, 1.0]
        assert profile.normalized_stats.persuasion == 0.40
        assert profile.normalized_stats.deception == 0.30
        assert profile.normalized_stats.patience == 0.20
        assert profile.normalized_stats.aggression == 0.10
        total_norm = (
            profile.normalized_stats.persuasion
            + profile.normalized_stats.deception
            + profile.normalized_stats.patience
            + profile.normalized_stats.aggression
        )
        assert round(total_norm, 4) == 1.0

        # Verify behavior directive generated without exposing raw inputs
        assert "Persuasion" in profile.behavior_directive
        assert "vector weighting" in profile.behavior_directive.lower()

    def test_attacker_negative_value_rejected(self):
        """Test that negative stat values are rejected with NegativeStatError."""
        raw = {
            "persuasion": -10,
            "deception": 50,
            "patience": 30,
            "aggression": 30,
        }
        with pytest.raises(NegativeStatError) as exc_info:
            build_attacker_agent_profile(raw)
        assert "cannot be negative" in str(exc_info.value)

    def test_attacker_excessive_allocation_rejected(self):
        """Test that allocation exceeding budget is rejected with StatBudgetExceededError."""
        raw = {
            "persuasion": 50,
            "deception": 40,
            "patience": 30,
            "aggression": 20,  # Sum = 140 > 100
        }
        with pytest.raises(StatBudgetExceededError) as exc_info:
            build_attacker_agent_profile(raw)
        assert "exceeds point budget" in str(exc_info.value)

    def test_attacker_under_allocation_rejected(self):
        """Test that allocation below required budget is rejected with InvalidStatAllocationError."""
        raw = {
            "persuasion": 20,
            "deception": 20,
            "patience": 20,
            "aggression": 20,  # Sum = 80 != 100
        }
        with pytest.raises(InvalidStatAllocationError) as exc_info:
            build_attacker_agent_profile(raw)
        assert "must equal required budget" in str(exc_info.value)

    def test_attacker_invalid_keys_rejected(self):
        """Test that missing or unexpected keys are rejected."""
        # Missing 'aggression'
        with pytest.raises(InvalidStatAllocationError) as exc_info:
            build_attacker_agent_profile({"persuasion": 40, "deception": 30, "patience": 30})
        assert "Missing required stats" in str(exc_info.value)

        # Unexpected extra key
        with pytest.raises(InvalidStatAllocationError) as exc_info:
            build_attacker_agent_profile({
                "persuasion": 25,
                "deception": 25,
                "patience": 25,
                "aggression": 25,
                "stealth": 0,
            })
        assert "Unexpected stats" in str(exc_info.value)

    # -----------------------------------------------------------------------
    # WARDEN Role Tests
    # -----------------------------------------------------------------------

    def test_valid_warden_allocation(self):
        """Test valid 100-point allocation for Warden."""
        raw = {
            "skepticism": 35,
            "rigidity": 35,
            "empathy": 10,
            "memory": 20,
        }
        profile = build_warden_agent_profile(raw)

        assert isinstance(profile, WardenAgentProfile)
        assert profile.raw_allocation.skepticism == 35
        assert profile.raw_allocation.rigidity == 35
        assert profile.raw_allocation.empathy == 10
        assert profile.raw_allocation.memory == 20
        assert profile.raw_allocation.total == 100

        # Verify normalization to floats [0.0, 1.0]
        assert profile.normalized_stats.skepticism == 0.35
        assert profile.normalized_stats.rigidity == 0.35
        assert profile.normalized_stats.empathy == 0.10
        assert profile.normalized_stats.memory == 0.20
        total_norm = (
            profile.normalized_stats.skepticism
            + profile.normalized_stats.rigidity
            + profile.normalized_stats.empathy
            + profile.normalized_stats.memory
        )
        assert round(total_norm, 4) == 1.0

        # Verify defense directive generated
        assert "Warden defense stance" in profile.defense_directive

    def test_warden_negative_value_rejected(self):
        """Test that negative stat values for Warden are rejected."""
        raw = {
            "skepticism": 40,
            "rigidity": -5,
            "empathy": 35,
            "memory": 30,
        }
        with pytest.raises(NegativeStatError) as exc_info:
            build_warden_agent_profile(raw)
        assert "cannot be negative" in str(exc_info.value)

    def test_warden_excessive_allocation_rejected(self):
        """Test that allocation exceeding budget for Warden is rejected."""
        raw = {
            "skepticism": 50,
            "rigidity": 50,
            "empathy": 10,
            "memory": 10,  # Sum = 120 > 100
        }
        with pytest.raises(StatBudgetExceededError) as exc_info:
            build_warden_agent_profile(raw)
        assert "exceeds point budget" in str(exc_info.value)

    def test_warden_invalid_keys_rejected(self):
        """Test that wrong stats (e.g. attacker stats passed to warden) are rejected."""
        with pytest.raises(InvalidStatAllocationError) as exc_info:
            build_warden_agent_profile({
                "persuasion": 25,
                "deception": 25,
                "patience": 25,
                "aggression": 25,
            })
        assert "Missing required stats" in str(exc_info.value)

    # -----------------------------------------------------------------------
    # Direct Model Validation Tests
    # -----------------------------------------------------------------------

    def test_pydantic_direct_instantiation_validation(self):
        """Test Pydantic model validation on direct instantiation."""
        # Forbids negative through Field(ge=0)
        with pytest.raises(ValidationError):
            AttackerStatAllocation(persuasion=-1, deception=25, patience=25, aggression=25)

        with pytest.raises(ValidationError):
            WardenStatAllocation(skepticism=25, rigidity=-1, empathy=25, memory=25)

        # Forbids extra fields
        with pytest.raises(ValidationError):
            AttackerStatAllocation(persuasion=25, deception=25, patience=25, aggression=25, extra=10)

    def test_custom_budget_support(self):
        """Test pipeline supports custom configurable budget values."""
        custom_budget = 50
        raw = {
            "persuasion": 20,
            "deception": 15,
            "patience": 10,
            "aggression": 5,
        }
        profile = build_attacker_agent_profile(raw, budget=custom_budget)
        assert profile.raw_allocation.total == 50
        assert profile.normalized_stats.persuasion == 0.40  # 20 / 50
        assert profile.normalized_stats.deception == 0.30   # 15 / 50
        assert profile.normalized_stats.patience == 0.20    # 10 / 50
        assert profile.normalized_stats.aggression == 0.10  # 5 / 50
