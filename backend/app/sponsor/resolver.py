"""
Mon Arcade — Sponsor Resolver
Resolves active sponsor content without coupling presentation components to sponsor infrastructure.
Guarantees non-blocking execution: if database or sponsor network is unavailable,
it gracefully provides fallback Mon Arcade branding so UI rendering is never interrupted.

Hierarchy: Game > Game Action > Game State > Sponsor
Sponsors must never alter game rules, timers, outcomes, or state transitions.
"""

import logging
from typing import Dict, Any, Optional

from backend.app.sponsor.models import PlacementSlot, ResolvedSponsor
from backend.app.sponsor.repository import SponsorRepository, get_sponsor_repository
from backend.app.sponsor.service import SponsorCampaignService

logger = logging.getLogger("mon_arcade.sponsor")


class SponsorResolver:
    """Resolves active sponsor content without coupling the UI directly to sponsor infrastructure.
    
    Guarantees non-blocking execution: if database or sponsor network is unavailable,
    it gracefully provides fallback Mon Arcade branding so UI rendering is never interrupted.
    """

    FALLBACK_SPONSOR: Dict[str, Any] = {
        "id": "fallback-mon-arcade",
        "placement_id": "pl_fallback_marquee",
        "campaign_id": None,
        "name": "MON ARCADE FOUNDATION",
        "tagline": "HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS",
        "url": "https://monad.xyz",
        "logo": None,
        "is_fallback": True,
    }

    def __init__(
        self,
        db_pool=None,
        repo: Optional[SponsorRepository] = None,
        service: Optional[SponsorCampaignService] = None,
    ):
        self._db_pool = db_pool
        self._repo = repo or get_sponsor_repository()
        self._service = service or SponsorCampaignService(repository=self._repo)

    async def resolve_sponsor(self, placement_type: str = "marquee") -> ResolvedSponsor:
        """Resolve typed ResolvedSponsor model. Fails safely to fallback branding on any error."""
        try:
            return await self._service.resolve_placement(placement_type)
        except Exception as e:
            logger.warning(f"Failed to resolve active sponsor: {e}. Falling back to default branding.")
            slot = PlacementSlot.normalize(placement_type)
            return ResolvedSponsor(
                placement_id=f"pl_fallback_{slot.value.lower()}",
                campaign_id=None,
                sponsor_id="fallback-mon-arcade",
                name="MON ARCADE FOUNDATION",
                tagline="HIGH-PERFORMANCE ON-CHAIN ENTERTAINMENT EXPERIMENTS",
                url="https://monad.xyz",
                logo=None,
                slot_type=slot,
                is_fallback=True,
            )

    async def get_active_sponsor(self, placement_type: str = "marquee") -> Dict[str, Any]:
        """Resolve active sponsor dictionary for API responses. Non-blocking with immediate fallback."""
        try:
            resolved: ResolvedSponsor = await self.resolve_sponsor(placement_type)
            return {
                "id": resolved.sponsor_id,
                "placement_id": resolved.placement_id,
                "campaign_id": resolved.campaign_id,
                "name": resolved.name,
                "tagline": resolved.tagline,
                "url": resolved.url,
                "logo": resolved.logo,
                "is_fallback": resolved.is_fallback,
            }
        except Exception as e:
            logger.warning(f"Unexpected error in get_active_sponsor: {e}. Falling back to default branding.")
            slot = PlacementSlot.normalize(placement_type)
            fallback = dict(self.FALLBACK_SPONSOR)
            fallback["placement_id"] = f"pl_fallback_{slot.value.lower()}"
            return fallback

    async def record_impression(self, placement_id: str) -> bool:
        """Record an impression asynchronously without blocking the client."""
        try:
            return await self._repo.record_impression(placement_id)
        except Exception as e:
            logger.warning(f"Could not record impression: {e}")
            return False

    async def record_click(self, placement_id: str) -> bool:
        """Record a click asynchronously without blocking the client."""
        try:
            return await self._repo.record_click(placement_id)
        except Exception as e:
            logger.warning(f"Could not record click: {e}")
            return False


def get_sponsor_resolver() -> SponsorResolver:
    """Factory returning the default SponsorResolver instance."""
    return SponsorResolver()
