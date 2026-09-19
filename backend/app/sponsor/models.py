"""
Mon Arcade — Sponsor Domain Models
Authoritative lightweight representations for Sponsors, Campaigns, Placements, Sponsor Vaults, and Analytics.
Strictly decoupled from UI; operates with local MockBlockchain and existing PostgreSQL schema.
Sponsor UI is always subordinate to gameplay: Game > Game Action > Game State > Sponsor.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import re
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class CampaignStatus(str, Enum):
    """Authoritative lifecycle states of a sponsor campaign."""
    DRAFT = "DRAFT"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    FUNDED = "FUNDED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"


class SponsorVaultStatus(str, Enum):
    """Funding status of a campaign's locked escrow vault."""
    PENDING = "PENDING"
    FUNDED = "FUNDED"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"


class PlacementSlot(str, Enum):
    """Approved placement locations across Mon Arcade screens.
    Sponsor content is strictly subordinate to gameplay."""
    HOME_MARQUEE = "HOME_MARQUEE"  # Home screen subordinate banner
    BLUFF_LOBBY = "BLUFF_LOBBY"    # Bluff or Bust setup/lobby screen
    VAULT_SETUP = "VAULT_SETUP"    # Monad Vault setup/loadout screen

    # Aliases for schema / backward compatibility
    MARQUEE = "MARQUEE"
    FOOTER = "FOOTER"
    GAME_CARD = "GAME_CARD"

    @classmethod
    def normalize(cls, slot: Union[str, "PlacementSlot"]) -> "PlacementSlot":
        """Normalize slot name to standard approved Mon Arcade placement."""
        if isinstance(slot, cls):
            return slot
        s = str(slot).upper().strip().replace("-", "_")
        if s in ("HOME", "HOME_MARQUEE", "HOME_BANNER", "MARQUEE"):
            return cls.HOME_MARQUEE
        if s in ("BLUFF", "BLUFF_LOBBY", "BLUFF_FOOTER"):
            return cls.BLUFF_LOBBY
        if s in ("VAULT", "VAULT_SETUP", "VAULT_FOOTER"):
            return cls.VAULT_SETUP
        if s in ("FOOTER",):
            return cls.FOOTER
        if s in ("GAME_CARD", "GAME"):
            return cls.GAME_CARD
        return cls.HOME_MARQUEE


# Valid state machine transitions
ALLOWED_CAMPAIGN_TRANSITIONS: Dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.PAYMENT_PENDING},
    CampaignStatus.PAYMENT_PENDING: {CampaignStatus.FUNDED, CampaignStatus.PAYMENT_FAILED},
    CampaignStatus.PAYMENT_FAILED: {CampaignStatus.PAYMENT_PENDING},
    CampaignStatus.FUNDED: {CampaignStatus.ACTIVE, CampaignStatus.EXPIRED},
    CampaignStatus.ACTIVE: {CampaignStatus.EXPIRED},
    CampaignStatus.EXPIRED: set(),
}

ETHEREUM_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------

class Sponsor(BaseModel):
    """Represents a sponsor brand entity in Mon Arcade."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sponsor_id: str = Field(..., description="Unique sponsor identifier")
    name: str = Field(..., min_length=1, max_length=128, description="Brand/project display name")
    wallet: str = Field(..., description="Monad/EVM wallet address for sponsor actions")
    logo: Optional[str] = Field(default=None, max_length=512, description="Optional brand logo URL")
    website: str = Field(..., min_length=1, max_length=512, description="Destination website URL")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return self.sponsor_id

    @field_validator("wallet")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        cleaned = v.strip()
        if not ETHEREUM_ADDRESS_REGEX.match(cleaned):
            raise ValueError(f"Invalid wallet address format: {cleaned}. Must be 0x followed by 40 hex characters.")
        return cleaned

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: str) -> str:
        cleaned = v.strip()
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError(f"Website URL must start with http:// or https://: {cleaned}")
        return cleaned


class Campaign(BaseModel):
    """Represents a sponsor advertising campaign reserving arcade placement."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaign_id: str = Field(..., description="Unique campaign identifier")
    sponsor_id: str = Field(..., description="Foreign key reference to Sponsor")
    placement: PlacementSlot = Field(default=PlacementSlot.HOME_MARQUEE, description="Reserved slot type")
    start_time: Optional[datetime] = Field(default=None, description="Active start timestamp")
    end_time: Optional[datetime] = Field(default=None, description="Campaign expiration timestamp")
    budget: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Budget allocated in MON")
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT, description="Current campaign status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return self.campaign_id

    @property
    def start_at(self) -> Optional[datetime]:
        return self.start_time

    @property
    def end_at(self) -> Optional[datetime]:
        return self.end_time

    @model_validator(mode="after")
    def validate_dates(self) -> "Campaign":
        if self.start_time and self.end_time:
            if self.end_time < self.start_time:
                raise ValueError("Campaign end_time must be greater than or equal to start_time.")
        return self

    def can_transition_to(self, new_status: CampaignStatus) -> bool:
        """Check if transitioning from current status to new_status is allowed."""
        return new_status in ALLOWED_CAMPAIGN_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: CampaignStatus) -> "Campaign":
        """Transition campaign to a new lifecycle status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid campaign state transition: cannot move from {self.status.value} to {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        return self

    def mark_payment_pending(self) -> "Campaign":
        return self.transition_to(CampaignStatus.PAYMENT_PENDING)

    def mark_payment_failed(self) -> "Campaign":
        return self.transition_to(CampaignStatus.PAYMENT_FAILED)

    def mark_funded(self) -> "Campaign":
        return self.transition_to(CampaignStatus.FUNDED)

    def activate(self, start: Optional[datetime] = None, end: Optional[datetime] = None) -> "Campaign":
        """Activate campaign. Requires campaign to be FUNDED first."""
        now = datetime.now(timezone.utc)
        target_start = start or self.start_time or now
        target_end = end or self.end_time

        if target_end and target_end < now:
            raise ValueError(f"Cannot activate expired campaign: end_time {target_end} is in the past.")

        if target_start and target_end and target_end < target_start:
            raise ValueError("Campaign end_time must be greater than or equal to start_time.")

        self.transition_to(CampaignStatus.ACTIVE)
        self.start_time = target_start
        self.end_time = target_end
        return self

    def expire(self) -> "Campaign":
        self.transition_to(CampaignStatus.EXPIRED)
        self.end_time = datetime.now(timezone.utc)
        return self


class Placement(BaseModel):
    """Represents a slot reservation for a campaign across Mon Arcade screens."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    placement_id: str = Field(..., description="Unique placement identifier")
    campaign_id: str = Field(..., description="Target campaign identifier")
    slot_type: PlacementSlot = Field(default=PlacementSlot.HOME_MARQUEE, description="Approved screen location")
    active: bool = Field(default=True, description="Whether placement is currently active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SponsorVault(BaseModel):
    """Authoritative local escrow/vault holding deposited campaign funds."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    vault_id: str = Field(..., description="Unique vault identifier")
    campaign_id: str = Field(..., description="Campaign associated with this vault")
    deposit_transaction: Optional[str] = Field(default=None, description="Mock/On-chain transaction hash")
    amount: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Escrowed amount in MON")
    status: SponsorVaultStatus = Field(default=SponsorVaultStatus.PENDING, description="Funding status")
    is_mock: bool = Field(default=True, description="Explicit flag indicating local/mock settlement")
    chain: str = Field(default="monad-mock-local", description="Blockchain network identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return self.vault_id

    @property
    def deposit_tx(self) -> Optional[str]:
        return self.deposit_transaction

    def confirm_deposit(self, tx_hash: str, deposit_amount: Optional[Decimal] = None) -> "SponsorVault":
        """Confirm receipt of sponsor funding deposit."""
        self.deposit_transaction = tx_hash
        if deposit_amount is not None:
            if deposit_amount < Decimal("0.0"):
                raise ValueError("Deposit amount cannot be negative.")
            self.amount = deposit_amount
        self.status = SponsorVaultStatus.FUNDED
        self.updated_at = datetime.now(timezone.utc)
        return self

    def release(self) -> "SponsorVault":
        """Mark escrow funds released to arcade treasury upon fulfillment."""
        if self.status != SponsorVaultStatus.FUNDED:
            raise ValueError(f"Cannot release funds from vault in {self.status.value} status.")
        self.status = SponsorVaultStatus.RELEASED
        self.updated_at = datetime.now(timezone.utc)
        return self

    def refund(self) -> "SponsorVault":
        """Refund escrowed funds back to sponsor wallet."""
        if self.status not in (SponsorVaultStatus.FUNDED, SponsorVaultStatus.PENDING):
            raise ValueError(f"Cannot refund vault in {self.status.value} status.")
        self.status = SponsorVaultStatus.REFUNDED
        self.updated_at = datetime.now(timezone.utc)
        return self


class Analytics(BaseModel):
    """Telemetry record tracking attention metrics for a sponsor campaign."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaign_id: str = Field(..., description="Target campaign identifier")
    impressions: int = Field(default=0, ge=0, description="Verified display events")
    clicks: int = Field(default=0, ge=0, description="Verified user interaction events")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Snapshot timestamp")

    @property
    def click_through_rate(self) -> float:
        """Calculate CTR percentage rounded to 2 decimal places."""
        if self.impressions <= 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100.0, 2)


class ResolvedSponsor(BaseModel):
    """Subordinate sponsor display model returned to frontend presentation components."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    placement_id: str = Field(..., description="Placement ID for telemetry attribution")
    campaign_id: Optional[str] = Field(default=None, description="Campaign ID if active")
    sponsor_id: str = Field(..., description="Sponsor identifier")
    name: str = Field(..., description="Brand display name")
    tagline: str = Field(..., description="Short marketing tagline")
    url: str = Field(..., description="Destination website URL")
    logo: Optional[str] = Field(default=None, description="Optional logo image URL")
    slot_type: PlacementSlot = Field(default=PlacementSlot.HOME_MARQUEE, description="Placement slot")
    is_fallback: bool = Field(default=False, description="True if default Mon Arcade branding is active")
