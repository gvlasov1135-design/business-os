import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from modules.documents.models import DocumentStatus


class DocumentFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checksum_sha256: str
    size_bytes: int
    storage_key: str
    created_at: datetime


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    original_filename: str
    content_type: str
    created_at: datetime
    file: DocumentFileRead | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionRead] = Field(default_factory=list)


class DocumentUploadResult(BaseModel):
    document: DocumentRead
    duplicate: bool = False
    existing_document_id: uuid.UUID | None = None
