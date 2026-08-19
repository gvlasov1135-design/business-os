import csv
import io
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import AppError
from modules.ingestion import service
from modules.ingestion.schemas import ImportResponse


def parse_csv_rows(data: bytes) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AppError("CSV has no header row", status_code=400, code="csv_empty_header")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=1):
        cleaned = {key.strip(): (value.strip() if isinstance(value, str) else value) for key, value in row.items() if key}
        if not any(cleaned.values()):
            continue
        if "lead_id" not in cleaned and "external_id" not in cleaned:
            raise AppError(
                f"CSV row {index} requires lead_id or external_id",
                status_code=400,
                code="csv_missing_external_id",
            )
        rows.append(cleaned)
    if not rows:
        raise AppError("CSV contains no data rows", status_code=400, code="csv_empty")
    return rows


async def import_csv(
    session: AsyncSession,
    source_id: uuid.UUID,
    data: bytes,
) -> list[ImportResponse]:
    source = await service.get_source(session, source_id)
    if source.source_type.value not in ("csv", "crm"):
        raise AppError(
            "CSV import requires source_type csv or crm",
            status_code=400,
            code="csv_source_type_invalid",
        )
    rows = parse_csv_rows(data)
    results: list[ImportResponse] = []
    for row in rows:
        results.append(await service.import_record(session, source_id, row))
    return results
