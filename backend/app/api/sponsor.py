"""
Mon Arcade — Sponsor API Router
Provides minimal endpoints for:
- Sponsor entity registration
- Campaign creation & funding
- Campaign status & analytics retrieval
- Non-blocking active sponsor resolution
- Telemetry recording (impressions & clicks)

Sponsor UI is always subordinate to gameplay. Sponsors never alter game rules.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from backend.app.sponsor import get_sponsor_resolver, get_sponsor_repository, SponsorCampaignService
from backend.app.sponsor.models import PlacementSlot
from backend.app.models.schemas import (
    SponsorResponse,
    CreateSponsorRequest,
    SponsorItemResponse,
    CreateCampaignRequest,
    CampaignResponse,
    CampaignDetailResponse,
    FundingInitiationResponse,
    ConfirmFundingRequest,
    FailFundingRequest,
)

router = APIRouter(prefix="/sponsor", tags=["sponsor"])


def _get_service() -> SponsorCampaignService:
    repo = get_sponsor_repository()
    return SponsorCampaignService(repository=repo)


# ---------------------------------------------------------------------------
# 1. Sponsor Entity Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=SponsorItemResponse, status_code=201)
async def create_sponsor(req: CreateSponsorRequest):
    """Register a new sponsor entity with Monad wallet address and website URL."""
    service = _get_service()
    try:
        sponsor = await service.register_sponsor(
            name=req.name,
            wallet=req.wallet,
            website=req.website,
            logo=req.logo,
        )
        return SponsorItemResponse(
            id=sponsor.sponsor_id,
            name=sponsor.name,
            wallet=sponsor.wallet,
            website=sponsor.website,
            logo=sponsor.logo,
            created_at=sponsor.created_at.isoformat() if sponsor.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/entity/{sponsor_id}", response_model=SponsorItemResponse)
async def get_sponsor(sponsor_id: str):
    """Retrieve details for a registered sponsor."""
    repo = get_sponsor_repository()
    sponsor = await repo.get_sponsor(sponsor_id)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return SponsorItemResponse(
        id=sponsor.sponsor_id,
        name=sponsor.name,
        wallet=sponsor.wallet,
        website=sponsor.website,
        logo=sponsor.logo,
        created_at=sponsor.created_at.isoformat() if sponsor.created_at else None,
    )


# ---------------------------------------------------------------------------
# 2. Campaign Endpoints
# ---------------------------------------------------------------------------

@router.post("/campaign", response_model=CampaignDetailResponse, status_code=201)
async def create_campaign(req: CreateCampaignRequest):
    """Create a new sponsor campaign. Optionally auto-funds via MockBlockchain for local dev."""
    service = _get_service()
    start_dt = datetime.fromisoformat(req.start_at) if req.start_at else None
    end_dt = datetime.fromisoformat(req.end_at) if req.end_at else None

    try:
        campaign = await service.create_campaign(
            sponsor_id=req.sponsor_id,
            budget=Decimal(str(req.budget)),
            placement=req.placement,
            start_time=start_dt,
            end_time=end_dt,
        )

        vault_dict = None
        if req.auto_fund:
            campaign, vault = await service.confirm_funding(campaign.campaign_id)
            await service.activate_campaign(campaign.campaign_id)
            vault_dict = {
                "id": vault.vault_id,
                "amount": float(vault.amount),
                "deposit_tx": vault.deposit_transaction,
                "status": vault.status.value,
                "is_mock": True,
                "chain": "monad-mock-local",
            }

        return CampaignDetailResponse(
            id=campaign.campaign_id,
            sponsor_id=campaign.sponsor_id,
            placement=campaign.placement.value,
            budget=float(campaign.budget),
            status=campaign.status.value,
            start_at=campaign.start_time.isoformat() if campaign.start_time else None,
            end_at=campaign.end_time.isoformat() if campaign.end_time else None,
            created_at=campaign.created_at.isoformat() if campaign.created_at else None,
            vault=vault_dict,
            analytics={"impressions": 0, "clicks": 0, "click_through_rate": 0.0},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaign/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(campaign_id: str):
    """Retrieve detailed campaign status, escrow vault record, and attention telemetry."""
    repo = get_sponsor_repository()
    campaign = await repo.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    vault = await repo.get_vault_by_campaign(campaign_id)
    analytics = await repo.get_analytics(campaign_id)

    vault_dict = None
    if vault:
        vault_dict = {
            "id": vault.vault_id,
            "amount": float(vault.amount),
            "deposit_tx": vault.deposit_transaction,
            "status": vault.status.value,
            "is_mock": True,
            "chain": "monad-mock-local",
        }

    return CampaignDetailResponse(
        id=campaign.campaign_id,
        sponsor_id=campaign.sponsor_id,
        placement=campaign.placement.value,
        budget=float(campaign.budget),
        status=campaign.status.value,
        start_at=campaign.start_time.isoformat() if campaign.start_time else None,
        end_at=campaign.end_time.isoformat() if campaign.end_time else None,
        created_at=campaign.created_at.isoformat() if campaign.created_at else None,
        vault=vault_dict,
        analytics={
            "impressions": analytics.impressions,
            "clicks": analytics.clicks,
            "click_through_rate": analytics.click_through_rate,
        },
    )


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(sponsor_id: Optional[str] = Query(None)):
    """List campaigns, optionally filtered by sponsor ID."""
    repo = get_sponsor_repository()
    campaigns = await repo.list_campaigns(sponsor_id=sponsor_id)
    return [
        CampaignResponse(
            id=c.campaign_id,
            sponsor_id=c.sponsor_id,
            placement=c.placement.value,
            budget=float(c.budget),
            status=c.status.value,
            start_at=c.start_time.isoformat() if c.start_time else None,
            end_at=c.end_time.isoformat() if c.end_time else None,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in campaigns
    ]


@router.post("/campaign/{campaign_id}/initiate-funding", response_model=FundingInitiationResponse)
async def initiate_funding(campaign_id: str):
    """Initiate funding flow: transitions campaign to PAYMENT_PENDING with mock deposit details."""
    service = _get_service()
    try:
        campaign = await service.initiate_payment(campaign_id)
        return FundingInitiationResponse(
            campaign_id=campaign.campaign_id,
            status=campaign.status.value,
            budget=float(campaign.budget),
            currency="MON",
            chain="monad-mock-local",
            is_mock=True,
            deposit_recipient="0xmock_arcade_sponsor_escrow_vault",
            instructions="[MOCK / LOCAL] Submit mock payment transaction via confirm-funding to simulate funding.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaign/{campaign_id}/confirm-funding", response_model=CampaignDetailResponse)
@router.post("/campaign/{campaign_id}/fund", response_model=CampaignDetailResponse)
async def confirm_funding(campaign_id: str, req: Optional[ConfirmFundingRequest] = None):
    """Confirm mock funding deposit, transitioning campaign to FUNDED and recording escrow."""
    service = _get_service()
    tx_hash = req.tx_hash if req else None
    auto_activate = req.auto_activate if req else False

    try:
        campaign, vault = await service.confirm_funding(campaign_id, tx_hash=tx_hash)
        if auto_activate:
            await service.activate_campaign(campaign_id)
        return await get_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaign/{campaign_id}/fail-funding", response_model=CampaignDetailResponse)
async def fail_funding(campaign_id: str, req: Optional[FailFundingRequest] = None):
    """Explicitly mark payment as PAYMENT_FAILED, enabling subsequent retry via initiate-funding."""
    service = _get_service()
    reason = req.reason if req else "Simulated mock payment failure"
    try:
        await service.fail_payment(campaign_id, reason=reason)
        return await get_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaign/{campaign_id}/activate", response_model=CampaignDetailResponse)
async def activate_campaign(campaign_id: str):
    """Activate a funded campaign, making its placements active."""
    service = _get_service()
    try:
        await service.activate_campaign(campaign_id)
        return await get_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# 3. Active Placement & Telemetry Endpoints
# ---------------------------------------------------------------------------

@router.get("/active", response_model=SponsorResponse)
async def get_active_sponsor(placement_type: str = "marquee"):
    """Resolve active sponsor for the requested placement slot without blocking."""
    resolver = get_sponsor_resolver()
    data = await resolver.get_active_sponsor(placement_type=placement_type)
    return SponsorResponse(**data)


@router.post("/impression/{placement_id}")
async def record_impression(placement_id: str):
    """Record verified display event asynchronously without blocking client."""
    resolver = get_sponsor_resolver()
    recorded = await resolver.record_impression(placement_id)
    return {"status": "ok", "recorded": recorded}


@router.post("/click/{placement_id}")
async def record_click(placement_id: str):
    """Record verified click event asynchronously without blocking client."""
    resolver = get_sponsor_resolver()
    recorded = await resolver.record_click(placement_id)
    return {"status": "ok", "recorded": recorded}
