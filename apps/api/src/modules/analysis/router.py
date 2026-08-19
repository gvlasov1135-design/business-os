import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.analysis import service
from modules.analysis.schemas import AIAnalysisRead, AnalysisCreate, RecommendationRead
from modules.auth.deps import require_roles

router = APIRouter(prefix="/api/v1/analyses", tags=["analysis"])


@router.post("", response_model=AIAnalysisRead, status_code=201)
async def create_analysis(
    payload: AnalysisCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "executive", "reviewer")),
) -> AIAnalysisRead:
    analysis = await service.create_analysis(session, payload.company_id, payload.question)
    recommendations = await service.list_recommendations(session, analysis.id)
    return AIAnalysisRead(
        **AIAnalysisRead.model_validate(analysis).model_dump(exclude={"recommendations"}),
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations],
    )


@router.get("/{analysis_id}", response_model=AIAnalysisRead)
async def get_analysis(
    analysis_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> AIAnalysisRead:
    analysis = await service.get_analysis(session, analysis_id)
    recommendations = await service.list_recommendations(session, analysis.id)
    return AIAnalysisRead(
        **AIAnalysisRead.model_validate(analysis).model_dump(exclude={"recommendations"}),
        recommendations=[RecommendationRead.model_validate(r) for r in recommendations],
    )
