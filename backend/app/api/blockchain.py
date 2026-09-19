from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.blockchain import get_blockchain_service

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


class SubmitTxRequest(BaseModel):
    tx_type: str
    user_id: str
    amount: float


@router.post("/tx")
async def submit_transaction(req: SubmitTxRequest):
    service = get_blockchain_service()
    result = await service.submit_transaction(
        tx_type=req.tx_type,
        user_id=req.user_id,
        amount=req.amount,
    )
    return result


@router.get("/verify/{tx_hash}")
async def verify_transaction(tx_hash: str):
    service = get_blockchain_service()
    is_valid = await service.verify_transaction(tx_hash)
    return {"tx_hash": tx_hash, "valid": is_valid}


@router.get("/balance/{wallet_address}")
async def get_balance(wallet_address: str):
    service = get_blockchain_service()
    return await service.get_balance(wallet_address)
