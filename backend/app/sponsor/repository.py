"""
Mon Arcade — Sponsor Repository
Dual-mode persistence layer for Sponsor, Campaign, Placement, Vault, and Analytics records.
Gracefully operates with in-memory storage when PostgreSQL is offline, ensuring reliable local testing.
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

logger = logging.getLogger("mon_arcade.sponsor.repo")


class SponsorRepository:
    """Repository handling persistence and queries for the Mon Arcade sponsor subsystem."""

    DEFAULT_FALLBACK_SPONSOR = Sponsor(
        sponsor_id="fallback-mon-arcade",
        name="MON ARCADE FOUNDATION",
        wallet="0x0000000000000000000000000000000000000000",
        website="https://monad.xyz",
        logo=None,
    )
    DEFAULT_FALLBACK_TAGLINE = "HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS"

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        # Local in-memory stores for offline/test operation
        self._sponsors: Dict[str, Sponsor] = {
            self.DEFAULT_FALLBACK_SPONSOR.sponsor_id: self.DEFAULT_FALLBACK_SPONSOR
        }
        self._campaigns: Dict[str, Campaign] = {}
        self._placements: Dict[str, Placement] = {}
        self._vaults: Dict[str, SponsorVault] = {}
        self._analytics: Dict[str, Analytics] = {}
        self._impressions: List[Dict[str, Any]] = []
        self._clicks: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # Sponsor Operations
    # -----------------------------------------------------------------------

    async def save_sponsor(self, sponsor: Sponsor) -> Sponsor:
        self._sponsors[sponsor.sponsor_id] = sponsor
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO sponsors (id, name, tagline, url, wallet, logo, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO UPDATE
                        SET name = EXCLUDED.name,
                            url = EXCLUDED.url,
                            wallet = EXCLUDED.wallet,
                            logo = EXCLUDED.logo;
                        """,
                        sponsor.sponsor_id,
                        sponsor.name,
                        self.DEFAULT_FALLBACK_TAGLINE,
                        sponsor.website,
                        sponsor.wallet,
                        sponsor.logo,
                        sponsor.created_at,
                    )
            except Exception as e:
                logger.warning(f"Could not persist sponsor to DB: {e}. Preserved in-memory.")
        return sponsor

    async def get_sponsor(self, sponsor_id: str) -> Optional[Sponsor]:
        if sponsor_id in self._sponsors:
            return self._sponsors[sponsor_id]

        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT * FROM sponsors WHERE id = $1", sponsor_id)
                    if row:
                        sp = Sponsor(
                            sponsor_id=row["id"],
                            name=row["name"],
                            wallet=row.get("wallet") or "0x0000000000000000000000000000000000000000",
                            logo=row.get("logo"),
                            website=row["url"],
                            created_at=row["created_at"],
                        )
                        self._sponsors[sp.sponsor_id] = sp
                        return sp
            except Exception as e:
                logger.warning(f"DB error fetching sponsor: {e}")
        return None

    # -----------------------------------------------------------------------
    # Campaign Operations
    # -----------------------------------------------------------------------

    async def save_campaign(self, campaign: Campaign) -> Campaign:
        self._campaigns[campaign.campaign_id] = campaign
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO campaigns (id, sponsor_id, name, status, budget, placement, start_time, end_time, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (id) DO UPDATE
                        SET status = EXCLUDED.status,
                            budget = EXCLUDED.budget,
                            start_time = EXCLUDED.start_time,
                            end_time = EXCLUDED.end_time,
                            updated_at = EXCLUDED.updated_at;
                        """,
                        campaign.campaign_id,
                        campaign.sponsor_id,
                        f"Campaign {campaign.campaign_id}",
                        campaign.status.value,
                        campaign.budget,
                        campaign.placement.value,
                        campaign.start_time,
                        campaign.end_time,
                        campaign.created_at,
                        campaign.updated_at,
                    )
            except Exception as e:
                logger.warning(f"Could not persist campaign to DB: {e}. Preserved in-memory.")
        return campaign

    async def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        if campaign_id in self._campaigns:
            return self._campaigns[campaign_id]

        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT * FROM campaigns WHERE id = $1", campaign_id)
                    if row:
                        cmp = Campaign(
                            campaign_id=row["id"],
                            sponsor_id=row["sponsor_id"],
                            placement=PlacementSlot.normalize(row.get("placement") or "HOME_MARQUEE"),
                            start_time=row.get("start_time"),
                            end_time=row.get("end_time"),
                            budget=Decimal(str(row["budget"])),
                            status=CampaignStatus(row["status"]),
                            created_at=row["created_at"],
                            updated_at=row.get("updated_at") or row["created_at"],
                        )
                        self._campaigns[cmp.campaign_id] = cmp
                        return cmp
            except Exception as e:
                logger.warning(f"DB error fetching campaign: {e}")
        return None

    async def list_campaigns(self, sponsor_id: Optional[str] = None) -> List[Campaign]:
        all_campaigns = list(self._campaigns.values())
        if sponsor_id:
            all_campaigns = [c for c in all_campaigns if c.sponsor_id == sponsor_id]
        return sorted(all_campaigns, key=lambda c: c.created_at, reverse=True)

    # -----------------------------------------------------------------------
    # Placement Operations
    # -----------------------------------------------------------------------

    async def save_placement(self, placement: Placement) -> Placement:
        self._placements[placement.placement_id] = placement
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO placements (id, campaign_id, slot_type, active, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO UPDATE
                        SET active = EXCLUDED.active;
                        """,
                        placement.placement_id,
                        placement.campaign_id,
                        placement.slot_type.value,
                        placement.active,
                        placement.created_at,
                    )
            except Exception as e:
                logger.warning(f"Could not persist placement to DB: {e}. Preserved in-memory.")
        return placement

    async def get_active_placement_for_slot(
        self, slot_type: PlacementSlot
    ) -> Optional[Tuple[Placement, Campaign, Sponsor]]:
        """Resolve highest-priority active placement, campaign, and sponsor for a slot."""
        now = datetime.now(timezone.utc)
        # 1. Search in-memory store
        for p in self._placements.values():
            if p.active and p.slot_type == slot_type:
                cmp = self._campaigns.get(p.campaign_id)
                if cmp and cmp.status == CampaignStatus.ACTIVE:
                    # Verify date constraints
                    if cmp.end_time and cmp.end_time < now:
                        cmp.status = CampaignStatus.EXPIRED
                        p.active = False
                        continue
                    if cmp.start_time and cmp.start_time > now:
                        continue
                    sp = self._sponsors.get(cmp.sponsor_id)
                    if sp:
                        return p, cmp, sp

        # 2. Query DB if connected
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT p.id as p_id, p.slot_type, p.active,
                               c.id as c_id, c.status, c.budget, c.start_time, c.end_time,
                               s.id as s_id, s.name as s_name, s.tagline as s_tagline, s.url as s_url, s.wallet, s.logo
                        FROM placements p
                        JOIN campaigns c ON c.id = p.campaign_id
                        JOIN sponsors s ON s.id = c.sponsor_id
                        WHERE p.slot_type = $1 AND p.active = TRUE AND c.status = 'ACTIVE'
                        ORDER BY p.created_at DESC
                        LIMIT 1;
                        """,
                        slot_type.value,
                    )
                    if row:
                        p = Placement(
                            placement_id=row["p_id"],
                            campaign_id=row["c_id"],
                            slot_type=PlacementSlot.normalize(row["slot_type"]),
                            active=row["active"],
                        )
                        cmp = Campaign(
                            campaign_id=row["c_id"],
                            sponsor_id=row["s_id"],
                            placement=PlacementSlot.normalize(row["slot_type"]),
                            start_time=row["start_time"],
                            end_time=row["end_time"],
                            budget=Decimal(str(row["budget"])),
                            status=CampaignStatus(row["status"]),
                        )
                        sp = Sponsor(
                            sponsor_id=row["s_id"],
                            name=row["s_name"],
                            wallet=row.get("wallet") or "0x0000000000000000000000000000000000000000",
                            logo=row.get("logo"),
                            website=row["s_url"],
                        )
                        return p, cmp, sp
            except Exception as e:
                logger.warning(f"DB error fetching active placement: {e}")

        return None

    # -----------------------------------------------------------------------
    # Sponsor Vault Operations
    # -----------------------------------------------------------------------

    async def save_vault(self, vault: SponsorVault) -> SponsorVault:
        self._vaults[vault.vault_id] = vault
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO sponsor_vaults (id, campaign_id, deposit_transaction, amount, status, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO UPDATE
                        SET deposit_transaction = EXCLUDED.deposit_transaction,
                            amount = EXCLUDED.amount,
                            status = EXCLUDED.status,
                            updated_at = EXCLUDED.updated_at;
                        """,
                        vault.vault_id,
                        vault.campaign_id,
                        vault.deposit_transaction,
                        vault.amount,
                        vault.status.value,
                        vault.created_at,
                        vault.updated_at,
                    )
            except Exception as e:
                logger.warning(f"Could not persist vault to DB: {e}. Preserved in-memory.")
        return vault

    async def get_vault_by_campaign(self, campaign_id: str) -> Optional[SponsorVault]:
        for v in self._vaults.values():
            if v.campaign_id == campaign_id:
                return v
        return None

    # -----------------------------------------------------------------------
    # Telemetry Operations (Impressions & Clicks)
    # -----------------------------------------------------------------------

    async def record_impression(self, placement_id: str) -> bool:
        self._impressions.append({
            "id": f"imp_{uuid.uuid4().hex[:16]}",
            "placement_id": placement_id,
            "created_at": datetime.now(timezone.utc),
        })
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO impressions (id, placement_id) VALUES ($1, $2)",
                        f"imp_{uuid.uuid4().hex[:16]}",
                        placement_id,
                    )
            except Exception as e:
                logger.warning(f"Could not write impression to DB: {e}")
        return True

    async def record_click(self, placement_id: str) -> bool:
        self._clicks.append({
            "id": f"clk_{uuid.uuid4().hex[:16]}",
            "placement_id": placement_id,
            "created_at": datetime.now(timezone.utc),
        })
        pool = self._db_pool
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO clicks (id, placement_id) VALUES ($1, $2)",
                        f"clk_{uuid.uuid4().hex[:16]}",
                        placement_id,
                    )
            except Exception as e:
                logger.warning(f"Could not write click to DB: {e}")
        return True

    async def get_analytics(self, campaign_id: str) -> Analytics:
        # Find placements belonging to this campaign
        placement_ids = {
            p.placement_id for p in self._placements.values() if p.campaign_id == campaign_id
        }
        imps = sum(1 for item in self._impressions if item["placement_id"] in placement_ids)
        clks = sum(1 for item in self._clicks if item["placement_id"] in placement_ids)

        return Analytics(
            campaign_id=campaign_id,
            impressions=imps,
            clicks=clks,
            timestamp=datetime.now(timezone.utc),
        )


_DEFAULT_REPO: Optional[SponsorRepository] = None

def get_sponsor_repository() -> SponsorRepository:
    """Singleton getter for SponsorRepository."""
    global _DEFAULT_REPO
    if _DEFAULT_REPO is None:
        from backend.app.db.database import get_db_pool
        _DEFAULT_REPO = SponsorRepository(db_pool=get_db_pool())
    return _DEFAULT_REPO
