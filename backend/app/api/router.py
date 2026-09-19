from typing import Optional
from fastapi import APIRouter, Query
from backend.app.api.health import router as health_router
from backend.app.api.sponsor import router as sponsor_router
from backend.app.api.blockchain import router as blockchain_router
from backend.app.api.ai import router as ai_router
from backend.app.api.bluff import router as bluff_router, get_match
from backend.app.api.vault import router as vault_router
from backend.app.api.challenge import router as challenge_router
from backend.app.api.first_blood import router as first_blood_router
from backend.app.game.bluff_models import BluffMatchClientView

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(sponsor_router)
api_router.include_router(blockchain_router)
api_router.include_router(ai_router)
api_router.include_router(bluff_router)
api_router.include_router(vault_router)
api_router.include_router(challenge_router)
api_router.include_router(first_blood_router)


@api_router.get("/match/{match_id}", response_model=BluffMatchClientView, tags=["match"])
async def restore_match(
    match_id: str,
    player_id: Optional[str] = Query(None, description="Requesting player ID for view sanitization"),
):
    """
    Authoritative match restoration endpoint.
    Restores game state after refresh, reconnect, or frontend reload.
    Guarantees opponent secrets and salts remain hidden until RESOLVED.
    """
    return await get_match(match_id=match_id, player_id=player_id)

