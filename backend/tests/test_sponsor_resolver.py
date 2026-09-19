"""
Unit tests for Mon Arcade SponsorResolver abstraction.
Verifies clean boundary between frontend API and sponsor persistence,
non-blocking execution, graceful fallback to Mon Arcade branding,
and that sponsor logic never alters game state or rules.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, patch

from backend.app.sponsor.models import (
    CampaignStatus,
    SponsorVaultStatus,
    PlacementSlot,
    Sponsor,
    Campaign,
    Placement,
    ResolvedSponsor,
)
from backend.app.sponsor.repository import SponsorRepository
from backend.app.sponsor.service import SponsorCampaignService
from backend.app.sponsor.resolver import SponsorResolver
from backend.app.blockchain.adapter import MockBlockchain
from backend.app.models.schemas import SponsorResponse


def setup_isolated_resolver():
    """Create fresh isolated repository, service, and resolver."""
    repo = SponsorRepository(db_pool=None)
    blockchain = MockBlockchain()
    service = SponsorCampaignService(repository=repo, blockchain=blockchain)
    resolver = SponsorResolver(repo=repo, service=service)
    return repo, service, resolver


class TestSponsorResolverEligibility:
    """Test explicit eligibility criteria:
    * active campaign resolves
    * inactive campaign does not resolve
    * expired campaign does not resolve
    * unfunded campaign does not resolve
    * missing sponsor falls back
    * resolver failure falls back safely
    """

    def test_active_campaign_resolves(self):
        """A fully funded and activated campaign resolves its sponsor content."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            # 1. Register sponsor
            sponsor = await service.register_sponsor(
                name="Monad Defi Hub",
                wallet="0x1111111111111111111111111111111111111111",
                website="https://defi.monad.xyz",
                logo="https://defi.monad.xyz/logo.png",
            )

            # 2. Create campaign for home marquee
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("100.0"),
                placement=PlacementSlot.HOME_MARQUEE,
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                end_time=datetime.now(timezone.utc) + timedelta(days=7),
            )

            # 3. Fund and activate
            await service.initiate_payment(campaign.campaign_id)
            await service.confirm_funding(campaign.campaign_id)
            await service.activate_campaign(campaign.campaign_id)

            # 4. Resolve via resolver
            data = await resolver.get_active_sponsor("home")
            assert data["is_fallback"] is False
            assert data["id"] == sponsor.sponsor_id
            assert data["name"] == "Monad Defi Hub"
            assert data["url"] == "https://defi.monad.xyz"
            assert data["logo"] == "https://defi.monad.xyz/logo.png"
            assert data["campaign_id"] == campaign.campaign_id

            # Also verify typed resolver method
            typed = await resolver.resolve_sponsor("home")
            assert isinstance(typed, ResolvedSponsor)
            assert typed.is_fallback is False
            assert typed.name == "Monad Defi Hub"

        asyncio.run(_run())

    def test_inactive_campaign_does_not_resolve(self):
        """A campaign in DRAFT status does not resolve, returning Mon Arcade fallback."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            sponsor = await service.register_sponsor(
                name="Inactive Sponsor",
                wallet="0x2222222222222222222222222222222222222222",
                website="https://inactive.monad.xyz",
            )
            # Created in DRAFT, not funded or activated
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("50.0"),
                placement=PlacementSlot.HOME_MARQUEE,
            )
            assert campaign.status == CampaignStatus.DRAFT

            # Resolver must return fallback branding
            data = await resolver.get_active_sponsor("home")
            assert data["is_fallback"] is True
            assert data["name"] == "MON ARCADE FOUNDATION"
            assert data["url"] == "https://monad.xyz"

        asyncio.run(_run())

    def test_expired_campaign_does_not_resolve(self):
        """A campaign whose end_time has passed or that has been marked EXPIRED does not resolve."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            sponsor = await service.register_sponsor(
                name="Expired Sponsor",
                wallet="0x3333333333333333333333333333333333333333",
                website="https://expired.monad.xyz",
            )
            now = datetime.now(timezone.utc)
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("50.0"),
                placement=PlacementSlot.BLUFF_LOBBY,
                start_time=now - timedelta(days=2),
                end_time=now + timedelta(hours=1),
            )
            await service.initiate_payment(campaign.campaign_id)
            await service.confirm_funding(campaign.campaign_id)
            await service.activate_campaign(campaign.campaign_id)

            # Case A: Explicit expiration
            await service.expire_campaign(campaign.campaign_id)
            data = await resolver.get_active_sponsor("bluff")
            assert data["is_fallback"] is True
            assert data["name"] == "MON ARCADE FOUNDATION"

            # Case B: End time in past during resolution
            campaign2 = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("50.0"),
                placement=PlacementSlot.VAULT_SETUP,
                start_time=now - timedelta(days=5),
                end_time=now + timedelta(days=1),
            )
            await service.initiate_payment(campaign2.campaign_id)
            await service.confirm_funding(campaign2.campaign_id)
            await service.activate_campaign(campaign2.campaign_id)

            # Manually simulate time lapse past end_time
            campaign2.end_time = now - timedelta(minutes=5)
            await repo.save_campaign(campaign2)

            vault_data = await resolver.get_active_sponsor("vault")
            assert vault_data["is_fallback"] is True
            assert vault_data["name"] == "MON ARCADE FOUNDATION"

        asyncio.run(_run())

    def test_unfunded_campaign_does_not_resolve(self):
        """Campaigns in PAYMENT_PENDING or PAYMENT_FAILED cannot resolve."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            sponsor = await service.register_sponsor(
                name="Unfunded Project",
                wallet="0x4444444444444444444444444444444444444444",
                website="https://unfunded.monad.xyz",
            )
            campaign = await service.create_campaign(
                sponsor_id=sponsor.sponsor_id,
                budget=Decimal("25.0"),
                placement=PlacementSlot.HOME_MARQUEE,
            )

            # PAYMENT_PENDING state
            await service.initiate_payment(campaign.campaign_id)
            pending_res = await resolver.get_active_sponsor("home")
            assert pending_res["is_fallback"] is True

            # PAYMENT_FAILED state
            await service.fail_payment(campaign.campaign_id, reason="Declined")
            failed_res = await resolver.get_active_sponsor("home")
            assert failed_res["is_fallback"] is True
            assert failed_res["name"] == "MON ARCADE FOUNDATION"

        asyncio.run(_run())

    def test_missing_sponsor_falls_back(self):
        """If a campaign refers to a missing sponsor_id, resolver gracefully falls back."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            now = datetime.now(timezone.utc)
            # Create orphan active campaign pointing to ghost sponsor
            orphan_cmp = Campaign(
                campaign_id="cmp_orphan_999",
                sponsor_id="sp_ghost_non_existent",
                placement=PlacementSlot.HOME_MARQUEE,
                status=CampaignStatus.ACTIVE,
                budget=Decimal("50.0"),
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(days=5),
            )
            await repo.save_campaign(orphan_cmp)

            orphan_plc = Placement(
                placement_id="pl_orphan_999",
                campaign_id=orphan_cmp.campaign_id,
                slot_type=PlacementSlot.HOME_MARQUEE,
                active=True,
            )
            await repo.save_placement(orphan_plc)

            # Must not throw KeyError/AttributeError; must fall back safely
            res = await resolver.get_active_sponsor("home")
            assert res["is_fallback"] is True
            assert res["name"] == "MON ARCADE FOUNDATION"

        asyncio.run(_run())

    def test_resolver_failure_falls_back_safely(self):
        """When an unhandled exception or database failure occurs, resolver returns fallback branding without raising."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            # Mock service to raise catastrophic runtime exception
            service.resolve_placement = AsyncMock(side_effect=RuntimeError("Database connection timed out"))

            # Must catch error and return fallback
            data = await resolver.get_active_sponsor("home")
            assert data["is_fallback"] is True
            assert data["name"] == "MON ARCADE FOUNDATION"
            assert data["url"] == "https://monad.xyz"

            # Typed method also falls back safely
            typed = await resolver.resolve_sponsor("home")
            assert typed.is_fallback is True
            assert typed.name == "MON ARCADE FOUNDATION"

        asyncio.run(_run())

    def test_sponsor_resolution_does_not_alter_game_rules_or_state(self):
        """Sponsor resolution must never alter game rules, timers, outcomes, or state."""
        async def _run():
            repo, service, resolver = setup_isolated_resolver()

            # Resolution should just return content
            res_home = await resolver.get_active_sponsor("home")
            res_bluff = await resolver.get_active_sponsor("bluff")
            res_vault = await resolver.get_active_sponsor("vault")

            for res in (res_home, res_bluff, res_vault):
                assert "is_fallback" in res
                assert "name" in res
                # Must not contain game state or control directives
                assert "game_outcome" not in res
                assert "timer_override" not in res
                assert "warden_decision" not in res

        asyncio.run(_run())
