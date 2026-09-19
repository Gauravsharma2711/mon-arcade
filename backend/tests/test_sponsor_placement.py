"""
Unit tests for Mon Arcade Sponsor Campaign and Placement system.
Verifies validation rules, placement resolution, funding/activation state flow,
and subordinate placement behavior across Mon Arcade screens.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from backend.app.sponsor.models import (
    CampaignStatus,
    SponsorVaultStatus,
    PlacementSlot,
    Sponsor,
    Campaign,
    Placement,
    SponsorVault,
    ResolvedSponsor,
)
from backend.app.sponsor.repository import SponsorRepository
from backend.app.sponsor.service import SponsorCampaignService
from backend.app.blockchain.adapter import MockBlockchain


def get_fresh_service():
    """Create a fresh isolated SponsorCampaignService with in-memory repository and MockBlockchain."""
    repo = SponsorRepository(db_pool=None)
    blockchain = MockBlockchain()
    return SponsorCampaignService(repository=repo, blockchain=blockchain)


class TestSponsorCampaignValidation:
    """Verify validation rules: campaign exists, sponsor exists, placement valid, dates valid, status valid."""

    def test_campaign_requires_existing_sponsor(self):
        """Creating a campaign for a non-existent sponsor must raise ValueError."""
        async def _run():
            service = get_fresh_service()
            with pytest.raises(ValueError, match="does not exist"):
                await service.create_campaign(
                    sponsor_id="non_existent_sponsor_id",
                    budget=Decimal("50.0"),
                    placement=PlacementSlot.HOME_MARQUEE,
                )
        asyncio.run(_run())

    def test_campaign_created_in_draft_status(self):
        """Newly created campaigns must start in DRAFT status and NOT be active."""
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Ecosystem Labs",
                wallet="0x1111111111111111111111111111111111111111",
                website="https://ecosystem.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("25.0"),
                placement=PlacementSlot.HOME_MARQUEE,
            )
            assert campaign.status == CampaignStatus.DRAFT
            assert campaign.sponsor_id == sponsor.sponsor_id
            assert campaign.budget == Decimal("25.0")

            # Placement must exist but be inactive
            placements = list(service.repo._placements.values())
            matching = [p for p in placements if p.campaign_id == campaign.campaign_id]
            assert len(matching) == 1
            assert matching[0].active is False

        asyncio.run(_run())

    def test_campaign_invalid_dates_rejected(self):
        """End time before start time or past end time must be rejected."""
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Date Test Sponsor",
                wallet="0x2222222222222222222222222222222222222222",
                website="https://datetest.monad.xyz",
            )
            now = datetime.now(timezone.utc)

            # End time before start time
            with pytest.raises(ValueError, match="end_time must be greater than or equal to start_time"):
                await service.create_campaign(
                    sponsor_id=sponsor.sponsor_id,
                    budget=Decimal("10.0"),
                    start_time=now + timedelta(days=5),
                    end_time=now + timedelta(days=2),
                )

            # End time in the past
            with pytest.raises(ValueError, match="past expiration date"):
                await service.create_campaign(
                    sponsor_id=sponsor.sponsor_id,
                    budget=Decimal("10.0"),
                    start_time=now - timedelta(days=10),
                    end_time=now - timedelta(days=2),
                )

        asyncio.run(_run())

    def test_cannot_activate_unfunded_campaign(self):
        """Campaign cannot be activated directly from DRAFT without funding."""
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Unfunded Sponsor",
                wallet="0x3333333333333333333333333333333333333333",
                website="https://unfunded.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("30.0"),
                placement=PlacementSlot.BLUFF_LOBBY,
            )

            with pytest.raises(ValueError, match="must be FUNDED first"):
                await service.activate_campaign(campaign.campaign_id)

        asyncio.run(_run())


class TestSponsorFundingAndActivationFlow:
    """Verify documented state flow: DRAFT -> PAYMENT_PENDING -> FUNDED -> ACTIVE -> EXPIRED."""

    def test_complete_funding_and_activation_flow(self):
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Monad Defi Hub",
                wallet="0x4444444444444444444444444444444444444444",
                website="https://defi.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("50.0"),
                placement=PlacementSlot.VAULT_SETUP,
            )
            assert campaign.status == CampaignStatus.DRAFT

            # 1. Initiate payment (DRAFT -> PAYMENT_PENDING)
            campaign = await service.initiate_payment(campaign.campaign_id)
            assert campaign.status == CampaignStatus.PAYMENT_PENDING

            # 2. Confirm funding via MockBlockchain (PAYMENT_PENDING -> FUNDED)
            campaign, vault = await service.confirm_funding(campaign.campaign_id)
            assert campaign.status == CampaignStatus.FUNDED
            assert vault.status == SponsorVaultStatus.FUNDED
            assert vault.amount == Decimal("50.0")
            assert vault.deposit_transaction.startswith("0xmock_")

            # 3. Activate campaign (FUNDED -> ACTIVE)
            campaign = await service.activate_campaign(campaign.campaign_id)
            assert campaign.status == CampaignStatus.ACTIVE

            # Placement record must now be active
            placements = [p for p in service.repo._placements.values() if p.campaign_id == campaign.campaign_id]
            assert len(placements) == 1
            assert placements[0].active is True

            # 4. Expire campaign (ACTIVE -> EXPIRED)
            campaign = await service.expire_campaign(campaign.campaign_id)
            assert campaign.status == CampaignStatus.EXPIRED
            assert placements[0].active is False

        asyncio.run(_run())

    def test_payment_failure_and_retry(self):
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Retry Brand",
                wallet="0x5555555555555555555555555555555555555555",
                website="https://retry.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("15.0"),
            )
            await service.initiate_payment(campaign.campaign_id)

            # Fail payment
            campaign = await service.fail_payment(campaign.campaign_id, reason="Insufficient balance")
            assert campaign.status == CampaignStatus.PAYMENT_FAILED

            # Retry payment
            campaign = await service.initiate_payment(campaign.campaign_id)
            assert campaign.status == CampaignStatus.PAYMENT_PENDING

            # Confirm
            campaign, vault = await service.confirm_funding(campaign.campaign_id)
            assert campaign.status == CampaignStatus.FUNDED

        asyncio.run(_run())


class TestPlacementResolution:
    """Verify minimal placement model for approved Mon Arcade screen locations."""

    def test_fallback_branding_when_no_active_campaign(self):
        """When no active campaign exists, resolves subordinate Mon Arcade Foundation fallback."""
        async def _run():
            service = get_fresh_service()
            resolved = await service.resolve_placement(PlacementSlot.HOME_MARQUEE)
            assert isinstance(resolved, ResolvedSponsor)
            assert resolved.is_fallback is True
            assert resolved.name == "MON ARCADE FOUNDATION"
            assert resolved.url == "https://monad.xyz"
            assert resolved.slot_type == PlacementSlot.HOME_MARQUEE

        asyncio.run(_run())

    def test_approved_screens_resolution(self):
        """Verify resolution across all approved Mon Arcade locations: Home, Bluff, Vault."""
        async def _run():
            service = get_fresh_service()
            for slot in (PlacementSlot.HOME_MARQUEE, PlacementSlot.BLUFF_LOBBY, PlacementSlot.VAULT_SETUP):
                resolved = await service.resolve_placement(slot)
                assert resolved.slot_type == slot
                assert resolved.is_fallback is True

        asyncio.run(_run())

    def test_active_campaign_resolution(self):
        """Active campaign is resolved for its designated slot."""
        async def _run():
            service = get_fresh_service()
            sponsor = await service.register_sponsor(
                name="Pixel Games Monad",
                wallet="0x6666666666666666666666666666666666666666",
                website="https://pixelgames.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("100.0"),
                placement=PlacementSlot.BLUFF_LOBBY,
            )
            # Fund and activate
            await service.initiate_payment(campaign.campaign_id)
            await service.confirm_funding(campaign.campaign_id)
            await service.activate_campaign(campaign.campaign_id)

            # Bluff lobby resolves active sponsor
            resolved = await service.resolve_placement(PlacementSlot.BLUFF_LOBBY)
            assert resolved.is_fallback is False
            assert resolved.name == "Pixel Games Monad"
            assert resolved.url == "https://pixelgames.monad.xyz"
            assert resolved.slot_type == PlacementSlot.BLUFF_LOBBY
            assert resolved.campaign_id == campaign.campaign_id

            # Vault setup still resolves fallback
            vault_resolved = await service.resolve_placement(PlacementSlot.VAULT_SETUP)
            assert vault_resolved.is_fallback is True

        asyncio.run(_run())

    def test_slot_normalization_aliases(self):
        """String aliases (e.g. 'home', 'bluff', 'vault', 'marquee') map to canonical approved slots."""
        assert PlacementSlot.normalize("home") == PlacementSlot.HOME_MARQUEE
        assert PlacementSlot.normalize("bluff") == PlacementSlot.BLUFF_LOBBY
        assert PlacementSlot.normalize("vault") == PlacementSlot.VAULT_SETUP
        assert PlacementSlot.normalize("marquee") == PlacementSlot.HOME_MARQUEE
        assert PlacementSlot.normalize("unknown_slot") == PlacementSlot.HOME_MARQUEE
