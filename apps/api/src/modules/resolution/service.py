import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.audit import write_audit
from common.errors import AppError
from modules.ingestion.models import RawRecord
from modules.resolution.models import (
    CandidateStatus,
    CanonicalEntity,
    EntityMatchCandidate,
    EntityMembership,
    EntityMergeEvent,
    EntityType,
    MatchMethod,
    MembershipStatus,
    MergeEventType,
)
from modules.resolution.schemas import (
    CanonicalEntityRead,
    EntityMatchCandidateRead,
    EntityMembershipRead,
    ResolveRawRecordResponse,
)


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text or None


def extract_match_keys(payload: dict[str, Any], external_id: str) -> dict[str, str]:
    """Ключи для exact / deterministic / candidate matching."""
    keys: dict[str, str] = {}
    exact_id = _norm(payload.get("lead_id") or payload.get("external_id") or external_id)
    if exact_id:
        keys["external_id"] = exact_id

    email = _norm(payload.get("email") or payload.get("contact_email"))
    if email:
        keys["email"] = email

    phone = _norm(payload.get("phone") or payload.get("contact_phone"))
    if phone:
        phone = re.sub(r"[^\d+]", "", phone)
        if phone:
            keys["phone"] = phone

    inn = _norm(payload.get("inn") or payload.get("tax_id"))
    if inn:
        keys["inn"] = inn

    name = _norm(
        payload.get("counterparty_name")
        or payload.get("company_name")
        or payload.get("contact_name")
        or payload.get("full_name")
    )
    if name:
        keys["name"] = name

    return keys


def _display_name(payload: dict[str, Any], external_id: str) -> str:
    for key in ("counterparty_name", "company_name", "contact_name", "full_name", "lead_id"):
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return external_id


def _entity_type_for_payload(payload: dict[str, Any]) -> EntityType:
    raw = payload.get("entity_type")
    if isinstance(raw, str):
        try:
            return EntityType(raw)
        except ValueError:
            pass
    if payload.get("employee_id") or payload.get("actual_actor"):
        # lead остаётся lead; employee только явно
        pass
    return EntityType.lead


async def get_entity(session: AsyncSession, entity_id: uuid.UUID) -> CanonicalEntity:
    entity = await session.get(CanonicalEntity, entity_id)
    if entity is None:
        raise AppError("Canonical entity not found", status_code=404, code="entity_not_found")
    return entity


async def get_candidate(session: AsyncSession, candidate_id: uuid.UUID) -> EntityMatchCandidate:
    candidate = await session.get(EntityMatchCandidate, candidate_id)
    if candidate is None:
        raise AppError("Match candidate not found", status_code=404, code="candidate_not_found")
    return candidate


async def list_entities(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
) -> list[CanonicalEntity]:
    stmt = select(CanonicalEntity).order_by(CanonicalEntity.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(CanonicalEntity.company_id == company_id)
    return list((await session.scalars(stmt)).all())


async def list_memberships(
    session: AsyncSession,
    *,
    entity_id: uuid.UUID | None = None,
    company_id: uuid.UUID | None = None,
    status: MembershipStatus | None = MembershipStatus.active,
) -> list[EntityMembership]:
    stmt = select(EntityMembership).order_by(EntityMembership.created_at.desc())
    if entity_id is not None:
        stmt = stmt.where(EntityMembership.entity_id == entity_id)
    if company_id is not None:
        stmt = stmt.where(EntityMembership.company_id == company_id)
    if status is not None:
        stmt = stmt.where(EntityMembership.status == status)
    return list((await session.scalars(stmt)).all())


async def list_candidates(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    status: CandidateStatus | None = None,
) -> list[EntityMatchCandidate]:
    stmt = select(EntityMatchCandidate).order_by(EntityMatchCandidate.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(EntityMatchCandidate.company_id == company_id)
    if status is not None:
        stmt = stmt.where(EntityMatchCandidate.status == status)
    return list((await session.scalars(stmt)).all())


async def list_merge_events(
    session: AsyncSession,
    *,
    company_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
) -> list[EntityMergeEvent]:
    stmt = select(EntityMergeEvent).order_by(EntityMergeEvent.created_at.desc())
    if company_id is not None:
        stmt = stmt.where(EntityMergeEvent.company_id == company_id)
    if entity_id is not None:
        stmt = stmt.where(EntityMergeEvent.entity_id == entity_id)
    return list((await session.scalars(stmt)).all())


async def pending_blocking_reasons(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> list[str]:
    stmt = select(EntityMatchCandidate).where(
        EntityMatchCandidate.company_id == company_id,
        EntityMatchCandidate.status == CandidateStatus.pending,
        EntityMatchCandidate.blocks_analysis.is_(True),
    )
    rows = list((await session.scalars(stmt)).all())
    return [
        f"Не подтверждён Entity Resolution ({row.match_method.value}: {row.match_key}={row.match_value})"
        for row in rows
    ]


async def recalculate_entity_trust(session: AsyncSession, entity: CanonicalEntity) -> float:
    memberships = await list_memberships(session, entity_id=entity.id, status=MembershipStatus.active)
    if not memberships:
        entity.trust_index = 0.5
    else:
        avg_conf = sum(m.confidence for m in memberships) / len(memberships)
        # подтверждённые объединения повышают trust; много источников — слегка выше
        source_bonus = min(0.1, 0.02 * max(0, len(memberships) - 1))
        entity.trust_index = round(min(0.99, 0.55 + 0.35 * avg_conf + source_bonus), 4)
    await session.flush()
    return entity.trust_index


async def _membership_for_raw(
    session: AsyncSession,
    raw_record_id: uuid.UUID,
) -> EntityMembership | None:
    return await session.scalar(
        select(EntityMembership).where(
            EntityMembership.raw_record_id == raw_record_id,
            EntityMembership.status == MembershipStatus.active,
        )
    )


async def _create_entity(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    entity_type: EntityType,
    display_name: str,
    attributes: dict[str, Any],
) -> CanonicalEntity:
    entity = CanonicalEntity(
        company_id=company_id,
        entity_type=entity_type,
        display_name=display_name,
        trust_index=0.7,
        attributes=attributes,
    )
    session.add(entity)
    await session.flush()
    return entity


async def _link_membership(
    session: AsyncSession,
    *,
    entity: CanonicalEntity,
    raw_record: RawRecord,
    match_method: MatchMethod,
    confidence: float,
    event_type: MergeEventType,
    candidate_id: uuid.UUID | None = None,
    note: str | None = None,
) -> EntityMembership:
    existing = await session.scalar(
        select(EntityMembership).where(EntityMembership.raw_record_id == raw_record.id)
    )
    if existing is not None:
        previous_entity_id = existing.entity_id
        existing.entity_id = entity.id
        existing.source_id = raw_record.source_id
        existing.external_id = raw_record.external_id
        existing.match_method = match_method
        existing.confidence = confidence
        existing.status = MembershipStatus.active
        session.add(
            EntityMergeEvent(
                company_id=raw_record.company_id,
                event_type=event_type,
                entity_id=entity.id,
                candidate_id=candidate_id,
                raw_record_id=raw_record.id,
                note=note,
                payload={
                    "match_method": match_method.value,
                    "confidence": confidence,
                    "external_id": raw_record.external_id,
                    "previous_entity_id": str(previous_entity_id),
                },
            )
        )
        await session.flush()
        if previous_entity_id != entity.id:
            previous = await session.get(CanonicalEntity, previous_entity_id)
            if previous is not None:
                await recalculate_entity_trust(session, previous)
        await recalculate_entity_trust(session, entity)
        return existing

    membership = EntityMembership(
        company_id=raw_record.company_id,
        entity_id=entity.id,
        raw_record_id=raw_record.id,
        source_id=raw_record.source_id,
        external_id=raw_record.external_id,
        match_method=match_method,
        confidence=confidence,
        status=MembershipStatus.active,
    )
    session.add(membership)
    session.add(
        EntityMergeEvent(
            company_id=raw_record.company_id,
            event_type=event_type,
            entity_id=entity.id,
            candidate_id=candidate_id,
            raw_record_id=raw_record.id,
            note=note,
            payload={
                "match_method": match_method.value,
                "confidence": confidence,
                "external_id": raw_record.external_id,
            },
        )
    )
    await session.flush()
    await recalculate_entity_trust(session, entity)
    return membership


async def _find_peer_by_key(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    match_key: str,
    match_value: str,
    exclude_raw_id: uuid.UUID,
) -> RawRecord | None:
    """Ищем другой raw_record с тем же ключом через membership attributes / payload scan."""
    stmt = select(RawRecord).where(
        RawRecord.company_id == company_id,
        RawRecord.id != exclude_raw_id,
    )
    peers = list((await session.scalars(stmt)).all())
    for peer in peers:
        peer_keys = extract_match_keys(peer.payload or {}, peer.external_id)
        if peer_keys.get(match_key) == match_value:
            return peer
    return None


async def _ensure_candidate(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    entity_type: EntityType,
    left: RawRecord,
    right: RawRecord,
    match_method: MatchMethod,
    confidence: float,
    match_key: str,
    match_value: str,
    proposed_entity_id: uuid.UUID | None,
    blocks_analysis: bool,
) -> EntityMatchCandidate:
    left_id, right_id = sorted([left.id, right.id], key=str)
    existing = await session.scalar(
        select(EntityMatchCandidate).where(
            EntityMatchCandidate.left_raw_record_id == left_id,
            EntityMatchCandidate.right_raw_record_id == right_id,
            EntityMatchCandidate.match_method == match_method,
        )
    )
    if existing is not None:
        return existing

    candidate = EntityMatchCandidate(
        company_id=company_id,
        entity_type=entity_type,
        left_raw_record_id=left_id,
        right_raw_record_id=right_id,
        proposed_entity_id=proposed_entity_id,
        match_method=match_method,
        confidence=confidence,
        match_key=match_key,
        match_value=match_value,
        status=CandidateStatus.pending,
        requires_confirmation=True,
        blocks_analysis=blocks_analysis,
        evidence={
            "left_external_id": left.external_id if left.id == left_id else right.external_id,
            "right_external_id": right.external_id if left.id == left_id else left.external_id,
        },
    )
    # fix evidence with actual left/right after sort
    left_rec = left if left.id == left_id else right
    right_rec = right if right.id == right_id else left
    candidate.evidence = {
        "left_external_id": left_rec.external_id,
        "right_external_id": right_rec.external_id,
        "left_raw_record_id": str(left_id),
        "right_raw_record_id": str(right_id),
    }
    session.add(candidate)
    await session.flush()
    await write_audit(
        session,
        action="resolution.candidate_created",
        entity_type="entity_match_candidate",
        entity_id=candidate.id,
        company_id=company_id,
        payload={
            "match_method": match_method.value,
            "match_key": match_key,
            "confidence": confidence,
            "blocks_analysis": blocks_analysis,
        },
    )
    return candidate


async def resolve_raw_record(
    session: AsyncSession,
    raw_record: RawRecord,
    *,
    commit: bool = False,
) -> ResolveRawRecordResponse:
    """Exact → auto-link; deterministic/name → candidate с подтверждением."""
    existing_membership = await _membership_for_raw(session, raw_record.id)
    if existing_membership is not None:
        entity = await get_entity(session, existing_membership.entity_id)
        return ResolveRawRecordResponse(
            entity=CanonicalEntityRead.model_validate(entity),
            membership=EntityMembershipRead.model_validate(existing_membership),
            candidates=[],
            auto_linked=False,
        )

    payload = raw_record.payload or {}
    keys = extract_match_keys(payload, raw_record.external_id)
    entity_type = _entity_type_for_payload(payload)
    display = _display_name(payload, raw_record.external_id)
    candidates: list[EntityMatchCandidate] = []

    # 1) Exact match by external_id against existing memberships
    if "external_id" in keys:
        peer_membership = await session.scalar(
            select(EntityMembership).where(
                EntityMembership.company_id == raw_record.company_id,
                EntityMembership.external_id == raw_record.external_id,
                EntityMembership.status == MembershipStatus.active,
                EntityMembership.raw_record_id != raw_record.id,
            )
        )
        if peer_membership is not None:
            entity = await get_entity(session, peer_membership.entity_id)
            membership = await _link_membership(
                session,
                entity=entity,
                raw_record=raw_record,
                match_method=MatchMethod.exact,
                confidence=1.0,
                event_type=MergeEventType.auto_link,
                note="exact external_id",
            )
            if commit:
                await session.commit()
            return ResolveRawRecordResponse(
                entity=CanonicalEntityRead.model_validate(entity),
                membership=EntityMembershipRead.model_validate(membership),
                candidates=[],
                auto_linked=True,
            )

    # 2) Deterministic keys → candidate (requires confirmation, blocks analysis)
    for key_name, confidence, blocks in (
        ("email", 0.95, True),
        ("phone", 0.92, True),
        ("inn", 0.98, True),
        ("name", 0.75, False),
    ):
        if key_name not in keys:
            continue
        peer = await _find_peer_by_key(
            session,
            company_id=raw_record.company_id,
            match_key=key_name,
            match_value=keys[key_name],
            exclude_raw_id=raw_record.id,
        )
        if peer is None:
            continue
        peer_membership = await _membership_for_raw(session, peer.id)
        proposed_id = peer_membership.entity_id if peer_membership else None
        method = MatchMethod.deterministic if key_name != "name" else MatchMethod.candidate
        candidate = await _ensure_candidate(
            session,
            company_id=raw_record.company_id,
            entity_type=entity_type,
            left=raw_record,
            right=peer,
            match_method=method,
            confidence=confidence,
            match_key=key_name,
            match_value=keys[key_name],
            proposed_entity_id=proposed_id,
            blocks_analysis=blocks,
        )
        candidates.append(candidate)

    # 3) Always create own canonical if no auto-link
    entity = await _create_entity(
        session,
        company_id=raw_record.company_id,
        entity_type=entity_type,
        display_name=display,
        attributes={"keys": keys, "external_id": raw_record.external_id},
    )
    membership = await _link_membership(
        session,
        entity=entity,
        raw_record=raw_record,
        match_method=MatchMethod.exact,
        confidence=1.0,
        event_type=MergeEventType.auto_link,
        note="new canonical entity",
    )
    # update proposed_entity on candidates that had none
    for candidate in candidates:
        if candidate.proposed_entity_id is None:
            candidate.proposed_entity_id = entity.id

    await write_audit(
        session,
        action="resolution.entity_created",
        entity_type="canonical_entity",
        entity_id=entity.id,
        company_id=raw_record.company_id,
        payload={"raw_record_id": str(raw_record.id), "candidates": len(candidates)},
    )
    await session.refresh(entity)
    await session.refresh(membership)
    for candidate in candidates:
        await session.refresh(candidate)
    if commit:
        await session.commit()
        await session.refresh(entity)
        await session.refresh(membership)

    return ResolveRawRecordResponse(
        entity=CanonicalEntityRead.model_validate(entity),
        membership=EntityMembershipRead.model_validate(membership),
        candidates=[EntityMatchCandidateRead.model_validate(c) for c in candidates],
        auto_linked=False,
    )


async def confirm_candidate(
    session: AsyncSession,
    candidate_id: uuid.UUID,
    *,
    note: str | None = None,
) -> EntityMatchCandidate:
    candidate = await get_candidate(session, candidate_id)
    if candidate.status != CandidateStatus.pending:
        raise AppError("Candidate already resolved", status_code=409, code="candidate_resolved")

    left = await session.get(RawRecord, candidate.left_raw_record_id)
    right = await session.get(RawRecord, candidate.right_raw_record_id)
    if left is None or right is None:
        raise AppError("Candidate raw records missing", status_code=400, code="candidate_records_missing")

    left_m = await _membership_for_raw(session, left.id)
    right_m = await _membership_for_raw(session, right.id)

    if candidate.proposed_entity_id is not None:
        target = await get_entity(session, candidate.proposed_entity_id)
    elif left_m is not None:
        target = await get_entity(session, left_m.entity_id)
    elif right_m is not None:
        target = await get_entity(session, right_m.entity_id)
    else:
        target = await _create_entity(
            session,
            company_id=candidate.company_id,
            entity_type=candidate.entity_type,
            display_name=candidate.match_value,
            attributes={"from_candidate": str(candidate.id)},
        )

    # Merge both under target; исходные raw_records сохраняются
    for record, membership in ((left, left_m), (right, right_m)):
        if membership is not None and membership.entity_id == target.id:
            continue
        await _link_membership(
            session,
            entity=target,
            raw_record=record,
            match_method=candidate.match_method,
            confidence=candidate.confidence,
            event_type=MergeEventType.merge,
            candidate_id=candidate.id,
            note=note or "confirmed candidate",
        )

    candidate.status = CandidateStatus.confirmed
    candidate.resolved_at = datetime.now(timezone.utc)
    candidate.proposed_entity_id = target.id
    await recalculate_entity_trust(session, target)
    await write_audit(
        session,
        action="resolution.candidate_confirmed",
        entity_type="entity_match_candidate",
        entity_id=candidate.id,
        company_id=candidate.company_id,
        payload={"entity_id": str(target.id), "note": note},
    )
    await session.commit()
    await session.refresh(candidate)
    return candidate


async def reject_candidate(
    session: AsyncSession,
    candidate_id: uuid.UUID,
    *,
    note: str | None = None,
) -> EntityMatchCandidate:
    candidate = await get_candidate(session, candidate_id)
    if candidate.status != CandidateStatus.pending:
        raise AppError("Candidate already resolved", status_code=409, code="candidate_resolved")
    candidate.status = CandidateStatus.rejected
    candidate.resolved_at = datetime.now(timezone.utc)
    await write_audit(
        session,
        action="resolution.candidate_rejected",
        entity_type="entity_match_candidate",
        entity_id=candidate.id,
        company_id=candidate.company_id,
        payload={"note": note},
    )
    await session.commit()
    await session.refresh(candidate)
    return candidate


async def split_membership(
    session: AsyncSession,
    membership_id: uuid.UUID,
    *,
    note: str | None = None,
) -> CanonicalEntity:
    membership = await session.get(EntityMembership, membership_id)
    if membership is None:
        raise AppError("Membership not found", status_code=404, code="membership_not_found")
    if membership.status != MembershipStatus.active:
        raise AppError("Membership already split", status_code=409, code="membership_split")

    raw = await session.get(RawRecord, membership.raw_record_id)
    if raw is None:
        raise AppError("Raw record not found", status_code=404, code="raw_record_not_found")

    old_entity = await get_entity(session, membership.entity_id)
    active_on_old = await list_memberships(session, entity_id=old_entity.id, status=MembershipStatus.active)
    if len(active_on_old) <= 1:
        raise AppError(
            "Cannot split the only membership of an entity",
            status_code=400,
            code="split_requires_multiple",
        )

    payload = raw.payload or {}
    new_entity = await _create_entity(
        session,
        company_id=raw.company_id,
        entity_type=old_entity.entity_type,
        display_name=_display_name(payload, raw.external_id),
        attributes={"split_from": str(old_entity.id), "keys": extract_match_keys(payload, raw.external_id)},
    )
    await _link_membership(
        session,
        entity=new_entity,
        raw_record=raw,
        match_method=MatchMethod.exact,
        confidence=1.0,
        event_type=MergeEventType.split,
        note=note or "manual split",
    )
    await recalculate_entity_trust(session, old_entity)
    await write_audit(
        session,
        action="resolution.membership_split",
        entity_type="canonical_entity",
        entity_id=new_entity.id,
        company_id=raw.company_id,
        payload={
            "from_entity_id": str(old_entity.id),
            "membership_id": str(membership_id),
            "note": note,
        },
    )
    await session.commit()
    await session.refresh(new_entity)
    return new_entity


async def scan_company(
    session: AsyncSession,
    company_id: uuid.UUID,
) -> dict[str, Any]:
    """Повторный проход по raw_records без membership."""
    stmt = select(RawRecord).where(RawRecord.company_id == company_id).order_by(RawRecord.created_at)
    records = list((await session.scalars(stmt)).all())
    created_entities = 0
    created_candidates = 0
    for record in records:
        existing = await _membership_for_raw(session, record.id)
        if existing is not None:
            continue
        result = await resolve_raw_record(session, record, commit=False)
        if result.entity is not None:
            created_entities += 1
        created_candidates += len(result.candidates)
    await session.commit()
    return {
        "scanned": len(records),
        "created_entities": created_entities,
        "created_candidates": created_candidates,
    }
