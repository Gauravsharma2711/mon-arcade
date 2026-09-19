from pydantic import BaseModel
from typing import Optional, Dict, Any


class HealthResponse(BaseModel):
    status: str = "ok"


class DetailedHealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
    database: str
    adapters: Dict[str, str]


class SponsorResponse(BaseModel):
    id: str
    name: str
    tagline: str
    url: str
    is_fallback: bool = False
    placement_id: Optional[str] = None
    campaign_id: Optional[str] = None
    logo: Optional[str] = None


class CreateSponsorRequest(BaseModel):
    name: str
    wallet: str
    website: str
    logo: Optional[str] = None


class SponsorItemResponse(BaseModel):
    id: str
    name: str
    wallet: str
    website: str
    logo: Optional[str] = None
    created_at: Optional[str] = None


class CreateCampaignRequest(BaseModel):
    sponsor_id: str
    placement: str = "marquee"
    budget: float = 0.0
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    auto_fund: bool = False


class CampaignResponse(BaseModel):
    id: str
    sponsor_id: str
    placement: str
    budget: float
    status: str
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    created_at: Optional[str] = None


class CampaignDetailResponse(BaseModel):
    id: str
    sponsor_id: str
    placement: str
    budget: float
    status: str
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    created_at: Optional[str] = None
    vault: Optional[Dict[str, Any]] = None
    analytics: Optional[Dict[str, Any]] = None


class FundingInitiationResponse(BaseModel):
    campaign_id: str
    status: str
    budget: float
    currency: str = "MON"
    chain: str = "monad-mock-local"
    is_mock: bool = True
    deposit_recipient: str
    instructions: str


class ConfirmFundingRequest(BaseModel):
    tx_hash: Optional[str] = None
    auto_activate: bool = False


class FailFundingRequest(BaseModel):
    reason: str = "Simulated mock payment failure"


class MatchSession(BaseModel):
    id: str
    game_type: str
    status: str
    created_at: str
