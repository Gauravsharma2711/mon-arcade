"""
Mon Arcade — First Blood / Early Arcade Player REST API
Endpoints to record and query early player participation.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.db.first_blood_repo import default_first_blood_repo, FirstBloodRecord

router = APIRouter(prefix="/first-blood", tags=["first-blood"])


class RecordParticipationRequest(BaseModel):
    wallet: str = Field(..., min_length=1, description="Player wallet address")
    game: str = Field("VAULT", description="Arcade game played ('VAULT' or 'BLUFF')")


class FirstBloodResponse(BaseModel):
    wallet: str
    first_participation_at: str
    player_number: Optional[int] = None
    first_game: str
    is_first_time: bool = False


@router.post("/record", response_model=FirstBloodResponse)
async def record_player_participation(req: RecordParticipationRequest):
    """
    Record player completion/participation in Bluff or Vault.
    Guarantees first participation timestamp is preserved and never duplicated.
    """
    if not req.wallet.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet address cannot be empty.",
        )

    rec, is_first = await default_first_blood_repo.record_participation(
        wallet=req.wallet.strip(),
        game=req.game.strip(),
    )

    return FirstBloodResponse(
        wallet=rec.wallet,
        first_participation_at=rec.first_participation_at.isoformat(),
        player_number=rec.player_number,
        first_game=rec.first_game,
        is_first_time=is_first,
    )


@router.get("/{wallet}", response_model=FirstBloodResponse)
async def get_player_first_blood(wallet: str):
    """Query if a wallet has an early arcade player record."""
    rec = await default_first_blood_repo.get_record(wallet)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No participation record found for wallet '{wallet}'.",
        )

    return FirstBloodResponse(
        wallet=rec.wallet,
        first_participation_at=rec.first_participation_at.isoformat(),
        player_number=rec.player_number,
        first_game=rec.first_game,
        is_first_time=False,
    )
