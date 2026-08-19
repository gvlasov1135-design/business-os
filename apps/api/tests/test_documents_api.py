import io

import pytest


async def _bootstrap_company(client):
    response = await client.post("/api/v1/identity/bootstrap")
    assert response.status_code == 201
    return response.json()["company"]["id"]


@pytest.mark.asyncio
async def test_upload_document_and_download(client):
    company_id = await _bootstrap_company(client)
    content = b"%PDF-1.4 demo sales policy"

    upload = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id, "title": "Sales Policy"},
        files={"file": ("policy.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert upload.status_code == 201
    payload = upload.json()
    assert payload["duplicate"] is False
    assert payload["document"]["status"] == "stored"
    assert payload["document"]["title"] == "Sales Policy"
    assert len(payload["document"]["versions"]) == 1

    document_id = payload["document"]["id"]
    version_id = payload["document"]["versions"][0]["id"]

    download = await client.get(f"/api/v1/documents/{document_id}/versions/{version_id}/file")
    assert download.status_code == 200
    assert download.content == content


@pytest.mark.asyncio
async def test_upload_duplicate_returns_conflict(client):
    company_id = await _bootstrap_company(client)
    content = b"%PDF-1.4 same bytes"

    first = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id},
        files={"file": ("a.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id},
        files={"file": ("b.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert second.status_code == 409
    body = second.json()
    assert body["duplicate"] is True
    assert body["existing_document_id"] == first.json()["document"]["id"]


@pytest.mark.asyncio
async def test_reject_unsupported_file_type(client):
    company_id = await _bootstrap_company(client)
    response = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_file_type"


@pytest.mark.asyncio
async def test_add_new_version(client):
    company_id = await _bootstrap_company(client)
    first = await client.post(
        "/api/v1/documents",
        data={"company_id": company_id},
        files={"file": ("v1.pdf", io.BytesIO(b"%PDF-1.4 v1"), "application/pdf")},
    )
    document_id = first.json()["document"]["id"]

    second = await client.post(
        f"/api/v1/documents/{document_id}/versions",
        files={"file": ("v2.pdf", io.BytesIO(b"%PDF-1.4 v2"), "application/pdf")},
    )
    assert second.status_code == 201
    versions = second.json()["document"]["versions"]
    assert [item["version_number"] for item in versions] == [1, 2]
