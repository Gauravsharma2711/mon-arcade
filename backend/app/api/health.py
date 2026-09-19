from fastapi import APIRouter
from backend.app.config import settings
from backend.app.db.database import get_db_status
from backend.app.models.schemas import HealthResponse, DetailedHealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check returning { 'status': 'ok' }."""
    return HealthResponse(status="ok")


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check reporting database and adapter statuses."""
    return DetailedHealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database=get_db_status(),
        adapters={
            "blockchain": "mock" if settings.USE_MOCK_BLOCKCHAIN else "monad_rpc",
            "ai": "mock" if settings.USE_MOCK_AI else "llm_agent",
            "sponsor": "fallback_resolver",
        },
    )
