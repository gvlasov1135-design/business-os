import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class RoleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    created_at: datetime


class DepartmentCreate(BaseModel):
    company_id: uuid.UUID
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    code: str
    name: str
    created_at: datetime


class UserCreate(BaseModel):
    company_id: uuid.UUID
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    department_id: uuid.UUID | None = None
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    is_active: bool = True
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    department_id: uuid.UUID | None
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    roles: list[RoleRead] = Field(default_factory=list)


class BootstrapResponse(BaseModel):
    company: CompanyRead
    department: DepartmentRead
    role: RoleRead
    user: UserRead
