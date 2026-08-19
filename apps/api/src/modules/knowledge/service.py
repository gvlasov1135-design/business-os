import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.knowledge.models import (
    KnowledgeRecord,
    KnowledgeRecordStatus,
    KnowledgeRelation,
    KnowledgeRelationType,
)
from modules.knowledge.schemas import KnowledgeRelationCreate


async def get_knowledge(session: AsyncSession, record_id: uuid.UUID) -> KnowledgeRecord:
    record = await session.get(KnowledgeRecord, record_id)
    if record is None:
        raise AppError("Knowledge record not found", status_code=404, code="knowledge_not_found")
    return record


async def list_knowledge(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
    status: KnowledgeRecordStatus | None = None,
) -> list[KnowledgeRecord]:
    stmt = select(KnowledgeRecord).order_by(KnowledgeRecord.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(KnowledgeRecord.company_id == company_id)
    if status is not None:
        stmt = stmt.where(KnowledgeRecord.status == status)
    result = await session.scalars(stmt)
    return list(result.all())


async def search_knowledge(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    query: str,
    limit: int = 20,
) -> list[KnowledgeRecord]:
    q = query.strip()
    if not q:
        return []
    pattern = f"%{q}%"
    stmt = (
        select(KnowledgeRecord)
        .where(
            KnowledgeRecord.company_id == company_id,
            KnowledgeRecord.status == KnowledgeRecordStatus.active,
            or_(KnowledgeRecord.title.ilike(pattern), KnowledgeRecord.body.ilike(pattern)),
        )
        .order_by(KnowledgeRecord.created_at.desc())
        .limit(min(max(limit, 1), 100))
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def create_relation(
    session: AsyncSession,
    payload: KnowledgeRelationCreate,
) -> KnowledgeRelation:
    from_record = await get_knowledge(session, payload.from_record_id)
    to_record = await get_knowledge(session, payload.to_record_id)
    if from_record.company_id != to_record.company_id:
        raise AppError("Records must belong to same company", status_code=400, code="relation_company_mismatch")
    if from_record.company_id != payload.company_id:
        raise AppError("company_id mismatch", status_code=400, code="relation_company_mismatch")
    if payload.from_record_id == payload.to_record_id:
        raise AppError("Self-relation is not allowed", status_code=400, code="relation_self")

    existing = await session.scalar(
        select(KnowledgeRelation).where(
            KnowledgeRelation.from_record_id == payload.from_record_id,
            KnowledgeRelation.to_record_id == payload.to_record_id,
            KnowledgeRelation.relation_type == payload.relation_type,
        )
    )
    if existing:
        raise AppError("Relation already exists", status_code=409, code="relation_exists")

    relation = KnowledgeRelation(
        company_id=payload.company_id,
        from_record_id=payload.from_record_id,
        to_record_id=payload.to_record_id,
        relation_type=payload.relation_type,
    )
    session.add(relation)
    await session.flush()
    await write_audit(
        session,
        action="knowledge.relation_created",
        entity_type="knowledge_relation",
        entity_id=relation.id,
        company_id=payload.company_id,
        payload={
            "from": str(payload.from_record_id),
            "to": str(payload.to_record_id),
            "type": payload.relation_type.value,
        },
    )
    await session.commit()
    await session.refresh(relation)
    return relation


async def ensure_relation(
    session: AsyncSession,
    payload: KnowledgeRelationCreate,
) -> KnowledgeRelation:
    existing = await session.scalar(
        select(KnowledgeRelation).where(
            KnowledgeRelation.from_record_id == payload.from_record_id,
            KnowledgeRelation.to_record_id == payload.to_record_id,
            KnowledgeRelation.relation_type == payload.relation_type,
        )
    )
    if existing:
        return existing
    return await create_relation(session, payload)


async def list_relations(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    record_id: uuid.UUID | None = None,
) -> list[KnowledgeRelation]:
    stmt = select(KnowledgeRelation).order_by(KnowledgeRelation.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(KnowledgeRelation.company_id == company_id)
    if record_id is not None:
        stmt = stmt.where(
            or_(
                KnowledgeRelation.from_record_id == record_id,
                KnowledgeRelation.to_record_id == record_id,
            )
        )
    result = await session.scalars(stmt)
    return list(result.all())
