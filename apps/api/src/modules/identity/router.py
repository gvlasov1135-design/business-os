import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import AppError
from common.rate_limit import check_rate_limit
from config.settings import Settings, get_settings
from infrastructure.db import get_db
from modules.auth.deps import require_roles
from modules.identity import service
from modules.identity.schemas import (
    BootstrapResponse,
    CompanyCreate,
    CompanyRead,
    DepartmentCreate,
    DepartmentRead,
    RoleCreate,
    RoleRead,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])


@router.post("/companies", response_model=CompanyRead, status_code=201)
async def create_company(
    payload: CompanyCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin")),
) -> CompanyRead:
    company = await service.create_company(session, payload)
    return CompanyRead.model_validate(company)


@router.get("/companies", response_model=list[CompanyRead])
async def list_companies(session: AsyncSession = Depends(get_db)) -> list[CompanyRead]:
    companies = await service.list_companies(session)
    return [CompanyRead.model_validate(item) for item in companies]


@router.get("/companies/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CompanyRead:
    company = await service.get_company(session, company_id)
    return CompanyRead.model_validate(company)


@router.post("/roles", response_model=RoleRead, status_code=201)
async def create_role(
    payload: RoleCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin")),
) -> RoleRead:
    role = await service.create_role(session, payload)
    return RoleRead.model_validate(role)


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(session: AsyncSession = Depends(get_db)) -> list[RoleRead]:
    roles = await service.list_roles(session)
    return [RoleRead.model_validate(item) for item in roles]


@router.post("/departments", response_model=DepartmentRead, status_code=201)
async def create_department(
    payload: DepartmentCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin")),
) -> DepartmentRead:
    department = await service.create_department(session, payload)
    return DepartmentRead.model_validate(department)


@router.get("/departments", response_model=list[DepartmentRead])
async def list_departments(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[DepartmentRead]:
    departments = await service.list_departments(session, company_id=company_id)
    return [DepartmentRead.model_validate(item) for item in departments]


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
    _user=Depends(require_roles("admin")),
) -> UserRead:
    user = await service.create_user(session, payload)
    return UserRead.model_validate(user)


@router.get("/users", response_model=list[UserRead])
async def list_users(
    company_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[UserRead]:
    users = await service.list_users(session, company_id=company_id)
    return [UserRead.model_validate(item) for item in users]


@router.post("/identity/bootstrap", response_model=BootstrapResponse, status_code=201)
async def bootstrap_identity(
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BootstrapResponse:
    if not settings.bootstrap_enabled:
        raise AppError("Bootstrap disabled", status_code=403, code="bootstrap_disabled")
    client = request.client.host if request.client else "unknown"
    check_rate_limit(f"bootstrap:{client}", limit_per_minute=settings.rate_limit_per_minute)
    return await service.bootstrap_identity(session)
