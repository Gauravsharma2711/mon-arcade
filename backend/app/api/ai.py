from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.app.ai import get_agent_provider

router = APIRouter(prefix="/ai", tags=["ai"])


class WardenPromptRequest(BaseModel):
    turn: int = 1
    prompt: str


@router.post("/warden/evaluate")
async def evaluate_warden_prompt(req: WardenPromptRequest):
    provider = get_agent_provider()
    return await provider.generate_warden_response(turn=req.turn, prompt=req.prompt)


@router.get("/warden/stream")
async def stream_warden_response(turn: int = 1, prompt: str = "open"):
    provider = get_agent_provider()

    async def sse_generator():
        async for chunk in provider.stream_warden_response(turn=turn, prompt=prompt):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
