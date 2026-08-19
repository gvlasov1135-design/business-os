import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.audit import write_audit
from common.errors import AppError
from common.security import hash_password
from config.settings import get_settings
from modules.identity.models import Company, Department, Role, User
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


async def create_company(session: AsyncSession, payload: CompanyCreate) -> Company:
    existing = await session.scalar(select(Company).where(Company.name == payload.name))
    if existing:
        raise AppError("Company already exists", status_code=409, code="company_exists")

    company = Company(name=payload.name)
    session.add(company)
    await session.flush()
    await write_audit(
        session,
        action="company.created",
        entity_type="company",
        entity_id=company.id,
        company_id=company.id,
        payload={"name": company.name},
    )
    await session.commit()
    await session.refresh(company)
    return company


async def list_companies(session: AsyncSession) -> list[Company]:
    result = await session.scalars(select(Company).order_by(Company.name))
    return list(result.all())


async def get_company(session: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise AppError("Company not found", status_code=404, code="company_not_found")
    return company


async def create_role(session: AsyncSession, payload: RoleCreate) -> Role:
    existing = await session.scalar(select(Role).where(Role.code == payload.code))
    if existing:
        raise AppError("Role already exists", status_code=409, code="role_exists")

    role = Role(code=payload.code, name=payload.name)
    session.add(role)
    await session.flush()
    await write_audit(
        session,
        action="role.created",
        entity_type="role",
        entity_id=role.id,
        payload={"code": role.code, "name": role.name},
    )
    await session.commit()
    await session.refresh(role)
    return role


async def list_roles(session: AsyncSession) -> list[Role]:
    result = await session.scalars(select(Role).order_by(Role.code))
    return list(result.all())


async def create_department(session: AsyncSession, payload: DepartmentCreate) -> Department:
    await get_company(session, payload.company_id)
    existing = await session.scalar(
        select(Department).where(
            Department.company_id == payload.company_id,
            Department.code == payload.code,
        )
    )
    if existing:
        raise AppError("Department already exists", status_code=409, code="department_exists")

    department = Department(
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
    )
    session.add(department)
    await session.flush()
    await write_audit(
        session,
        action="department.created",
        entity_type="department",
        entity_id=department.id,
        company_id=department.company_id,
        payload={"code": department.code, "name": department.name},
    )
    await session.commit()
    await session.refresh(department)
    return department


async def list_departments(session: AsyncSession, company_id: uuid.UUID | None = None) -> list[Department]:
    stmt = select(Department).order_by(Department.name)
    if company_id is not None:
        stmt = stmt.where(Department.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    await get_company(session, payload.company_id)

    if payload.department_id is not None:
        department = await session.get(Department, payload.department_id)
        if not department or department.company_id != payload.company_id:
            raise AppError("Department not found for company", status_code=404, code="department_not_found")

    existing = await session.scalar(
        select(User).where(User.company_id == payload.company_id, User.email == payload.email)
    )
    if existing:
        raise AppError("User already exists", status_code=409, code="user_exists")

    roles: list[Role] = []
    if payload.role_ids:
        result = await session.scalars(select(Role).where(Role.id.in_(payload.role_ids)))
        roles = list(result.all())
        if len(roles) != len(set(payload.role_ids)):
            raise AppError("One or more roles not found", status_code=404, code="role_not_found")

    user = User(
        company_id=payload.company_id,
        department_id=payload.department_id,
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password) if payload.password else None,
        is_active=payload.is_active,
        roles=roles,
    )
    session.add(user)
    await session.flush()
    await write_audit(
        session,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        company_id=user.company_id,
        payload={"email": user.email, "full_name": user.full_name},
    )
    await session.commit()

    loaded = await session.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == user.id)
    )
    assert loaded is not None
    return loaded


async def list_users(session: AsyncSession, company_id: uuid.UUID | None = None) -> list[User]:
    stmt = select(User).options(selectinload(User.roles)).order_by(User.email)
    if company_id is not None:
        stmt = stmt.where(User.company_id == company_id)
    result = await session.scalars(stmt)
    return list(result.all())


async def bootstrap_identity(session: AsyncSession) -> BootstrapResponse:
    existing = await session.scalar(select(Company).where(Company.name == "Demo Company"))
    if existing:
        raise AppError("Bootstrap already applied", status_code=409, code="bootstrap_exists")

    company = await create_company(session, CompanyCreate(name="Demo Company"))
    admin_role = await create_role(session, RoleCreate(code="admin", name="Administrator"))
    await create_role(session, RoleCreate(code="executive", name="Executive"))
    await create_role(session, RoleCreate(code="reviewer", name="Reviewer"))
    department = await create_department(
        session,
        DepartmentCreate(company_id=company.id, code="sales", name="Sales"),
    )
    user = await create_user(
        session,
        UserCreate(
            company_id=company.id,
            department_id=department.id,
            email="admin@example.com",
            full_name="Demo Admin",
            role_ids=[admin_role.id],
            password=get_settings().bootstrap_admin_password,
        ),
    )

    return BootstrapResponse(
        company=CompanyRead.model_validate(company),
        department=DepartmentRead.model_validate(department),
        role=RoleRead.model_validate(admin_role),
        user=UserRead.model_validate(user),
    )
