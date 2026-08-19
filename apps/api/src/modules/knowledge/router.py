import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.knowledge import service
from modules.knowledge.schemas import (
    KnowledgeRecordRead,
    KnowledgeRelationCreate,
    KnowledgeRelationRead,
    KnowledgeSearchResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeRecordRead])
async def list_knowledge_records(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[KnowledgeRecordRead]:
    records = await service.list_knowledge(session, company_id=company_id)
    return [KnowledgeRecordRead.model_validate(item) for item in records]


@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_records(
    company_id: uuid.UUID = Query(...),
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    records = await service.search_knowledge(session, company_id=company_id, query=q, limit=limit)
    return KnowledgeSearchResponse(
        query=q,
        results=[KnowledgeRecordRead.model_validate(item) for item in records],
    )


@router.post("/relations", response_model=KnowledgeRelationRead, status_code=201)
async def create_knowledge_relation(
    payload: KnowledgeRelationCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin", "reviewer", "executive")),
) -> KnowledgeRelationRead:
    relation = await service.create_relation(session, payload)
    return KnowledgeRelationRead.model_validate(relation)


@router.get("/relations", response_model=list[KnowledgeRelationRead])
async def list_knowledge_relations(
    company_id: uuid.UUID | None = Query(default=None),
    record_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[KnowledgeRelationRead]:
    relations = await service.list_relations(session, company_id=company_id, record_id=record_id)
    return [KnowledgeRelationRead.model_validate(item) for item in relations]


@router.get("/{record_id}", response_model=KnowledgeRecordRead)
async def get_knowledge_record(
    record_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> KnowledgeRecordRead:
    record = await service.get_knowledge(session, record_id)
    return KnowledgeRecordRead.model_validate(record)
