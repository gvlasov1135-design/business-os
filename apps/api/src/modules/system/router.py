from fastapi import APIRouter, Depends, Response
from fastapi.responses import PlainTextResponse

from config.settings import Settings, get_settings
from common.metrics import render_prometheus
from modules.system.schemas import HealthResponse, ReadinessResponse
from modules.system.service import get_readiness

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")


@router.get("/api/v1/system/readiness", response_model=ReadinessResponse)
async def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    result = await get_readiness(settings)
    if result.status == "error":
        response.status_code = 503
    return result
