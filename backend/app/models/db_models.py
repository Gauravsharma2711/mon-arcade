"""
Pydantic schemas representing the 11 PostgreSQL database tables.
Provides type safety for asyncpg record conversions without an ORM.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


# 1. User
class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    wallet_address: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# 2. Game Session
class GameSessionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    game_type: str  # 'bluff' or 'vault'
    user_id: Optional[str] = None
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


# 3. Bluff Match (Authoritative server-owned state)
class BluffMatchModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: Optional[str] = None
    opponent_id: Optional[str] = None
    stake_amount: Decimal = Decimal("0")
    creator_secret: Optional[int] = None  # Hidden until resolution
    opponent_secret: Optional[int] = None  # Hidden until resolution
    winner_id: Optional[str] = None
    status: str = "WAITING"
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# 4. Vault Match (Authoritative server-owned state)
class VaultMatchModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    challenger_id: Optional[str] = None
    warden_model: str = "mock-warden"
    entry_fee: Decimal = Decimal("0")
    pot_amount: Decimal = Decimal("0")
    turns_allowed: int = 3
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# 5. Vault Turn (Authoritative prompt & response turn)
class VaultTurnModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    turn_number: int
    attacker_prompt: str
    warden_response: str
    breach_triggered: bool = False
    created_at: Optional[datetime] = None


# 6. Sponsor
class SponsorModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tagline: str
    url: str
    wallet: Optional[str] = None
    logo: Optional[str] = None
    created_at: Optional[datetime] = None


# 7. Campaign
class CampaignModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sponsor_id: Optional[str] = None
    name: str
    status: str = "DRAFT"
    budget: Decimal = Decimal("0")
    placement: str = "MARQUEE"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# 8. Placement
class PlacementModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: Optional[str] = None
    slot_type: str  # 'marquee', 'footer', 'game_card'
    active: bool = True
    created_at: Optional[datetime] = None


# 9. Transaction (Monad on-chain action record)
class TransactionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    tx_hash: Optional[str] = None
    tx_type: str  # 'ENTRY_FEE', 'PAYOUT', 'SPONSOR_PAYMENT'
    amount: Decimal
    status: str = "PENDING"
    created_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None


# 10. Impression
class ImpressionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    placement_id: Optional[str] = None
    created_at: Optional[datetime] = None


# 11. Click
class ClickModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    placement_id: Optional[str] = None
    created_at: Optional[datetime] = None


# 12. Sponsor Vault (Escrow for campaign funding)
class SponsorVaultModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    deposit_transaction: Optional[str] = None
    amount: Decimal = Decimal("0")
    status: str = "PENDING"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# 13. Campaign Analytics (Aggregated attention metrics)
class CampaignAnalyticsModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    impressions: int = 0
    clicks: int = 0
    timestamp: Optional[datetime] = None
