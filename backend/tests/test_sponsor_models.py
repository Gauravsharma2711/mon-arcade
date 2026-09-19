"""
Unit tests for Mon Arcade Sponsor domain models.
Verifies Sponsor, Campaign, SponsorVault, and Analytics models, explicit state machine transitions,
validation constraints, and escrow funding states.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from backend.app.sponsor.models import (
    CampaignStatus,
    SponsorVaultStatus,
    PlacementSlot,
    Sponsor,
    Campaign,
    SponsorVault,
    Analytics,
    ALLOWED_CAMPAIGN_TRANSITIONS,
)


class TestSponsorModel:
    """Test Sponsor domain entity validation and constraints."""

    def test_valid_sponsor_creation(self):
        sponsor = Sponsor(
            sponsor_id="sp_test_100",
            name="Monad Labs",
            wallet="0x1234567890123456789012345678901234567890",
            logo="https://monad.xyz/logo.png",
            website="https://monad.xyz",
        )
        assert sponsor.sponsor_id == "sp_test_100"
        assert sponsor.name == "Monad Labs"
        assert sponsor.wallet == "0x1234567890123456789012345678901234567890"
        assert sponsor.logo == "https://monad.xyz/logo.png"
        assert sponsor.website == "https://monad.xyz"
        assert sponsor.created_at is not None

    def test_sponsor_without_logo(self):
        sponsor = Sponsor(
            sponsor_id="sp_test_101",
            name="Community Sponsor",
            wallet="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            website="http://community.monad.xyz",
        )
        assert sponsor.logo is None

    def test_invalid_wallet_address_raises_error(self):
        # Too short
        with pytest.raises(ValueError, match="Invalid wallet address format"):
            Sponsor(
                sponsor_id="sp_bad_1",
                name="Bad Wallet",
                wallet="0x1234",
                website="https://example.com",
            )

        # Missing 0x prefix
        with pytest.raises(ValueError, match="Invalid wallet address format"):
            Sponsor(
                sponsor_id="sp_bad_2",
                name="Bad Wallet",
                wallet="123456789012345678901234567890123456789012",
                website="https://example.com",
            )

    def test_invalid_website_url_raises_error(self):
        with pytest.raises(ValueError, match="Website URL must start with http"):
            Sponsor(
                sponsor_id="sp_bad_3",
                name="Bad Website",
                wallet="0x1234567890123456789012345678901234567890",
                website="ftp://invalid.com",
            )


class TestCampaignModel:
    """Test Campaign domain entity, placement slots, and state machine transitions."""

    def test_default_campaign_creation(self):
        campaign = Campaign(
            campaign_id="cmp_100",
            sponsor_id="sp_test_100",
            placement=PlacementSlot.MARQUEE,
            budget=Decimal("50.0"),
        )
        assert campaign.campaign_id == "cmp_100"
        assert campaign.sponsor_id == "sp_test_100"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.placement == PlacementSlot.MARQUEE
        assert campaign.budget == Decimal("50.0")

    def test_valid_lifecycle_transitions(self):
        campaign = Campaign(
            campaign_id="cmp_life_1",
            sponsor_id="sp_1",
            budget=Decimal("100.0"),
        )
        assert campaign.status == CampaignStatus.DRAFT

        # 1. DRAFT -> PAYMENT_PENDING
        campaign.mark_payment_pending()
        assert campaign.status == CampaignStatus.PAYMENT_PENDING

        # 2. PAYMENT_PENDING -> FUNDED
        campaign.mark_funded()
        assert campaign.status == CampaignStatus.FUNDED

        # 3. FUNDED -> ACTIVE
        start_ts = datetime.now(timezone.utc)
        campaign.activate(start=start_ts)
        assert campaign.status == CampaignStatus.ACTIVE
        assert campaign.start_time == start_ts

        # 4. ACTIVE -> EXPIRED
        campaign.expire()
        assert campaign.status == CampaignStatus.EXPIRED
        assert campaign.end_time is not None

    def test_payment_failure_and_retry_flow(self):
        """Verify PAYMENT_PENDING -> PAYMENT_FAILED and subsequent retry back to PAYMENT_PENDING."""
        campaign = Campaign(
            campaign_id="cmp_fail_1",
            sponsor_id="sp_1",
        )
        campaign.mark_payment_pending()
        assert campaign.status == CampaignStatus.PAYMENT_PENDING

        # Payment failure
        campaign.mark_payment_failed()
        assert campaign.status == CampaignStatus.PAYMENT_FAILED

        # Retry payment
        campaign.mark_payment_pending()
        assert campaign.status == CampaignStatus.PAYMENT_PENDING

        # Successful confirmation
        campaign.mark_funded()
        assert campaign.status == CampaignStatus.FUNDED

    def test_invalid_transitions_rejected(self):
        """Ensure illegal state jumps raise descriptive ValueError."""
        campaign = Campaign(
            campaign_id="cmp_illegal_1",
            sponsor_id="sp_1",
        )
        # Cannot jump from DRAFT straight to ACTIVE
        with pytest.raises(ValueError, match="Invalid campaign state transition"):
            campaign.activate()

        # Cannot jump from DRAFT to FUNDED directly
        with pytest.raises(ValueError, match="Invalid campaign state transition"):
            campaign.mark_funded()

        # Mark payment pending
        campaign.mark_payment_pending()

        # Cannot jump from PAYMENT_PENDING straight to EXPIRED
        with pytest.raises(ValueError, match="Invalid campaign state transition"):
            campaign.expire()


class TestSponsorVaultModel:
    """Test SponsorVault escrow mechanics and funding statuses."""

    def test_vault_initialization(self):
        vault = SponsorVault(
            vault_id="sv_100",
            campaign_id="cmp_100",
        )
        assert vault.vault_id == "sv_100"
        assert vault.campaign_id == "cmp_100"
        assert vault.status == SponsorVaultStatus.PENDING
        assert vault.amount == Decimal("0.0")
        assert vault.deposit_transaction is None

    def test_confirm_deposit(self):
        vault = SponsorVault(
            vault_id="sv_101",
            campaign_id="cmp_101",
        )
        vault.confirm_deposit(
            tx_hash="0xmock_deposit_9999",
            deposit_amount=Decimal("75.5"),
        )
        assert vault.status == SponsorVaultStatus.FUNDED
        assert vault.deposit_transaction == "0xmock_deposit_9999"
        assert vault.amount == Decimal("75.5")

    def test_release_and_refund(self):
        vault = SponsorVault(
            vault_id="sv_102",
            campaign_id="cmp_102",
        )
        vault.confirm_deposit(tx_hash="0xmock_deposit_1234", deposit_amount=Decimal("50.0"))

        # Release funds
        vault.release()
        assert vault.status == SponsorVaultStatus.RELEASED

        # Refunding an already released vault should fail
        with pytest.raises(ValueError, match="Cannot refund vault in RELEASED status"):
            vault.refund()

    def test_release_unfunded_vault_fails(self):
        vault = SponsorVault(
            vault_id="sv_103",
            campaign_id="cmp_103",
        )
        with pytest.raises(ValueError, match="Cannot release funds from vault in PENDING status"):
            vault.release()


class TestAnalyticsModel:
    """Test Analytics domain entity and CTR calculation."""

    def test_analytics_metrics(self):
        metrics = Analytics(
            campaign_id="cmp_100",
            impressions=1000,
            clicks=85,
        )
        assert metrics.campaign_id == "cmp_100"
        assert metrics.impressions == 1000
        assert metrics.clicks == 85
        assert metrics.click_through_rate == 8.5  # 85 / 1000 * 100

    def test_analytics_zero_impressions(self):
        metrics = Analytics(
            campaign_id="cmp_empty",
            impressions=0,
            clicks=0,
        )
        assert metrics.click_through_rate == 0.0

    def test_negative_metrics_prevented(self):
        with pytest.raises(ValueError):
            Analytics(
                campaign_id="cmp_negative",
                impressions=-10,
            )
