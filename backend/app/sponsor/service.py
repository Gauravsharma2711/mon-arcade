"""
Mon Arcade — Sponsor Campaign & Placement Service
Authoritative domain logic managing the Sponsor lifecycle:
Creation -> Validation -> Funding (MockBlockchain) -> Activation -> Expiration -> Placement Resolution.

Guarantees gameplay dominance: Sponsor UI is strictly subordinate to gameplay.
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import uuid
from typing import Optional, List, Dict, Any, Tuple

from backend.app.sponsor.models import (
    Sponsor,
    Campaign,
    Placement,
    SponsorVault,
    Analytics,
    CampaignStatus,
    SponsorVaultStatus,
    PlacementSlot,
    ResolvedSponsor,
)
from backend.app.sponsor.repository import SponsorRepository, get_sponsor_repository
from backend.app.blockchain import BlockchainService, get_blockchain_service
from typing import Union

logger = logging.getLogger("mon_arcade.sponsor.service")

UnionPlacement = Union[PlacementSlot, str]


class SponsorCampaignService:
    """Service governing sponsor entity registration, campaign state transitions, and placement resolution."""

    def __init__(
        self,
        repository: Optional[SponsorRepository] = None,
        blockchain: Optional[BlockchainService] = None,
    ):
        self.repo = repository or get_sponsor_repository()
        self.blockchain = blockchain or get_blockchain_service()

    # -----------------------------------------------------------------------
    # 1. Sponsor Registration
    # -----------------------------------------------------------------------

    async def register_sponsor(
        self,
        name: str,
        wallet: str,
        website: str,
        logo: Optional[str] = None,
        sponsor_id: Optional[str] = None,
    ) -> Sponsor:
        """Register a new sponsor brand entity with address and URL validation."""
        sid = sponsor_id or f"sp_{uuid.uuid4().hex[:12]}"
        sponsor = Sponsor(
            sponsor_id=sid,
            name=name,
            wallet=wallet,
            website=website,
            logo=logo,
            created_at=datetime.now(timezone.utc),
        )
        return await self.repo.save_sponsor(sponsor)

    # -----------------------------------------------------------------------
    # 2. Campaign Creation (DRAFT)
    # -----------------------------------------------------------------------

    async def create_campaign(
        self,
        sponsor_id: str,
        budget: Decimal,
        placement: UnionPlacement = PlacementSlot.HOME_MARQUEE,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        campaign_id: Optional[str] = None,
    ) -> Campaign:
        """Create a new campaign in DRAFT status after strict validation."""
        # 1. Validate sponsor exists
        sponsor = await self.repo.get_sponsor(sponsor_id)
        if not sponsor:
            raise ValueError(f"Sponsor with ID '{sponsor_id}' does not exist.")

        # 2. Validate placement slot
        slot = PlacementSlot.normalize(placement)

        # 3. Validate budget
        if budget < Decimal("0.0"):
            raise ValueError("Campaign budget cannot be negative.")

        # 4. Validate dates
        now = datetime.now(timezone.utc)
        if start_time and end_time and end_time < start_time:
            raise ValueError("Campaign end_time must be greater than or equal to start_time.")

        if end_time and end_time < now:
            raise ValueError(f"Cannot create campaign with past expiration date: {end_time}")

        cid = campaign_id or f"cmp_{uuid.uuid4().hex[:12]}"
        campaign = Campaign(
            campaign_id=cid,
            sponsor_id=sponsor_id,
            placement=slot,
            start_time=start_time,
            end_time=end_time,
            budget=budget,
            status=CampaignStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        await self.repo.save_campaign(campaign)

        # Create corresponding placement entry (inactive while in DRAFT)
        placement_record = Placement(
            placement_id=f"pl_{uuid.uuid4().hex[:12]}",
            campaign_id=cid,
            slot_type=slot,
            active=False,
            created_at=now,
        )
        await self.repo.save_placement(placement_record)

        return campaign

    # -----------------------------------------------------------------------
    # 3. Funding Flow (DRAFT -> PAYMENT_PENDING -> FUNDED)
    # -----------------------------------------------------------------------

    async def initiate_payment(self, campaign_id: str) -> Campaign:
        """Transition campaign to PAYMENT_PENDING awaiting on-chain/mock deposit."""
        campaign = await self.repo.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        campaign.mark_payment_pending()
        return await self.repo.save_campaign(campaign)

    async def confirm_funding(
        self,
        campaign_id: str,
        user_wallet: Optional[str] = None,
        tx_hash: Optional[str] = None,
    ) -> Tuple[Campaign, SponsorVault]:
        """Confirm deposit and transition campaign to FUNDED using MockBlockchain."""
        campaign = await self.repo.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        if campaign.status != CampaignStatus.PAYMENT_PENDING:
            if campaign.status == CampaignStatus.DRAFT:
                campaign.mark_payment_pending()
            elif campaign.status == CampaignStatus.FUNDED:
                # Already funded
                existing_vault = await self.repo.get_vault_by_campaign(campaign_id)
                return campaign, existing_vault
            else:
                raise ValueError(
                    f"Cannot fund campaign in status '{campaign.status.value}'. Must be PAYMENT_PENDING."
                )

        sponsor = await self.repo.get_sponsor(campaign.sponsor_id)
        wallet = user_wallet or (sponsor.wallet if sponsor else "0x0000000000000000000000000000000000000000")

        # Execute on-chain / mock transaction
        if not tx_hash:
            tx_res = await self.blockchain.submit_transaction(
                tx_type="SPONSOR_PAYMENT",
                user_id=wallet,
                amount=float(campaign.budget),
            )
            confirmed_hash = tx_res.get("tx_hash", f"0xmock_sponsor_{uuid.uuid4().hex[:12]}")
        else:
            is_valid = await self.blockchain.verify_transaction(tx_hash)
            if not is_valid:
                raise ValueError(f"Transaction verification failed for hash '{tx_hash}'.")
            confirmed_hash = tx_hash

        # Transition campaign to FUNDED
        campaign.mark_funded()
        await self.repo.save_campaign(campaign)

        # Create or update SponsorVault record
        vault_id = f"sv_{uuid.uuid4().hex[:12]}"
        vault = SponsorVault(
            vault_id=vault_id,
            campaign_id=campaign_id,
            deposit_transaction=confirmed_hash,
            amount=campaign.budget,
            status=SponsorVaultStatus.FUNDED,
            is_mock=True,
            chain="monad-mock-local",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await self.repo.save_vault(vault)

        return campaign, vault

    async def fail_payment(self, campaign_id: str, reason: str = "Transaction declined") -> Campaign:
        """Mark payment as failed, permitting subsequent retry."""
        campaign = await self.repo.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        if campaign.status != CampaignStatus.PAYMENT_PENDING:
            raise ValueError(f"Cannot fail payment for campaign in status '{campaign.status.value}'.")

        campaign.mark_payment_failed()
        logger.warning(f"Payment failed for campaign {campaign_id}: {reason}")
        return await self.repo.save_campaign(campaign)

    # -----------------------------------------------------------------------
    # 4. Activation Flow (FUNDED -> ACTIVE)
    # -----------------------------------------------------------------------

    async def activate_campaign(
        self,
        campaign_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Campaign:
        """Activate a funded campaign, making its placements live."""
        campaign = await self.repo.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        # Strict rule: Cannot activate unless FUNDED
        if campaign.status != CampaignStatus.FUNDED:
            raise ValueError(
                f"Cannot activate campaign in status '{campaign.status.value}'. Campaign must be FUNDED first."
            )

        now = datetime.now(timezone.utc)
        effective_start = start_time or campaign.start_time or now
        effective_end = end_time or campaign.end_time

        if effective_end and effective_end < now:
            raise ValueError(f"Cannot activate campaign: expiration date {effective_end} is in the past.")

        campaign.activate(start=effective_start, end=effective_end)
        await self.repo.save_campaign(campaign)

        # Activate all placement entries associated with this campaign
        for p in self.repo._placements.values():
            if p.campaign_id == campaign_id:
                p.active = True
                await self.repo.save_placement(p)

        return campaign

    # -----------------------------------------------------------------------
    # 5. Expiration Flow (ACTIVE -> EXPIRED)
    # -----------------------------------------------------------------------

    async def expire_campaign(self, campaign_id: str) -> Campaign:
        """Expire an active campaign, deactivating its placements."""
        campaign = await self.repo.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID '{campaign_id}' does not exist.")

        campaign.expire()
        await self.repo.save_campaign(campaign)

        for p in self.repo._placements.values():
            if p.campaign_id == campaign_id:
                p.active = False
                await self.repo.save_placement(p)

        return campaign

    # -----------------------------------------------------------------------
    # 6. Placement Resolution (Frontend query)
    # -----------------------------------------------------------------------

    async def resolve_placement(self, slot: UnionPlacement = "marquee") -> ResolvedSponsor:
        """Resolve active sponsor for the requested placement slot.
        Fails safely to subordinate default Mon Arcade Foundation branding."""
        slot_type = PlacementSlot.normalize(slot)

        match = await self.repo.get_active_placement_for_slot(slot_type)
        if match:
            placement, campaign, sponsor = match
            return ResolvedSponsor(
                placement_id=placement.placement_id,
                campaign_id=campaign.campaign_id,
                sponsor_id=sponsor.sponsor_id,
                name=sponsor.name,
                tagline=getattr(sponsor, "tagline", "HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS"),
                url=sponsor.website,
                logo=sponsor.logo,
                slot_type=placement.slot_type,
                is_fallback=False,
            )

        # Fallback subordinate branding
        fallback_sp = self.repo.DEFAULT_FALLBACK_SPONSOR
        return ResolvedSponsor(
            placement_id=f"pl_fallback_{slot_type.value.lower()}",
            campaign_id=None,
            sponsor_id=fallback_sp.sponsor_id,
            name=fallback_sp.name,
            tagline=self.repo.DEFAULT_FALLBACK_TAGLINE,
            url=fallback_sp.website,
            logo=fallback_sp.logo,
            slot_type=slot_type,
            is_fallback=True,
        )
