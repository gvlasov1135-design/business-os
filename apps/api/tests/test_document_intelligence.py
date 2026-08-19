import io

import pytest


async def _upload_policy(client) -> tuple[str, str, str]:
    bootstrap = await client.post("/api/v1/identity/bootstrap")
    company_id = bootstrap.json()["company"]["id"]
    content = (
        "Менеджер по продажам обязан связаться с новым лидом "
        "не позднее 15 минут после его создания."
    ).encode("utf-8")
    upload = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id, "title": "Sales Policy"},
        files={"file": ("policy.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()["document"]
    return document["id"], document["versions"][0]["id"], content.decode("utf-8")


@pytest.mark.asyncio
async def test_mock_extraction_creates_deadline_statement(client):
    document_id, version_id, text = await _upload_policy(client)

    extracted = await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")
    assert extracted.status_code == 201
    body = extracted.json()

    assert body["fragment"]["text"] == text
    assert body["statement"]["statement_type"] == "deadline"
    assert body["statement"]["status"] == "proposed"
    assert body["statement"]["value_structured"]["amount"] == 15
    assert body["statement"]["value_structured"]["unit"] == "minutes"
    assert body["statement"]["source_anchor"]["quote"]
    assert body["statement"]["source_anchor"]["fragment_id"] == body["fragment"]["id"]

    # Extraction is idempotent for the same version.
    again = await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")
    assert again.status_code == 201
    assert again.json()["statement"]["id"] == body["statement"]["id"]


@pytest.mark.asyncio
async def test_confirm_and_reject_statement_flow(client):
    document_id, version_id, _ = await _upload_policy(client)
    extracted = await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")
    statement_id = extracted.json()["statement"]["id"]

    confirmed = await client.post(f"/api/v1/statements/{statement_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    again = await client.post(f"/api/v1/statements/{statement_id}/confirm")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "statement_not_proposed"


@pytest.mark.asyncio
async def test_reject_proposed_statement(client):
    document_id, version_id, _ = await _upload_policy(client)
    extracted = await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")
    statement_id = extracted.json()["statement"]["id"]

    rejected = await client.post(f"/api/v1/statements/{statement_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_list_fragments_and_statements(client):
    document_id, version_id, _ = await _upload_policy(client)
    await client.post(f"/api/v1/documents/{document_id}/versions/{version_id}/extract")

    fragments = await client.get(f"/api/v1/documents/{document_id}/versions/{version_id}/fragments")
    assert fragments.status_code == 200
    assert len(fragments.json()) == 1

    statements = await client.get(f"/api/v1/documents/{document_id}/statements")
    assert statements.status_code == 200
    assert len(statements.json()) >= 3
    types = {item["statement_type"] for item in statements.json()}
    assert "deadline" in types
    assert "responsible" in types
    assert "obligation" in types


@pytest.mark.asyncio
async def test_extraction_unit():
    from modules.documents.extraction import build_mock_extraction

    result = build_mock_extraction(
        "Контакт с лидом не позднее 15 минут после создания.".encode("utf-8")
    )
    assert result.statement_value["amount"] == 15
    assert result.statement_value["unit"] == "minutes"
    assert any(item.statement_type == "deadline" for item in result.statements)
