import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.audit import write_audit
from common.errors import AppError
from common.security import create_access_token, verify_password
from config.settings import Settings
from modules.auth.schemas import LoginRequest, LoginResponse, AuthUserRead
from modules.identity.models import User


async def login(session: AsyncSession, settings: Settings, payload: LoginRequest) -> LoginResponse:
    stmt = select(User).options(selectinload(User.roles)).where(User.email == str(payload.email).lower())
    if payload.company_id is not None:
        stmt = stmt.where(User.company_id == payload.company_id)
    user = await session.scalar(stmt)
    if user is None or not user.is_active:
        raise AppError("Invalid credentials", status_code=401, code="invalid_credentials")
    if not verify_password(payload.password, user.password_hash):
        raise AppError("Invalid credentials", status_code=401, code="invalid_credentials")

    roles = [role.code for role in user.roles]
    token = create_access_token(
        settings,
        user_id=str(user.id),
        company_id=str(user.company_id),
        email=user.email,
        roles=roles,
    )
    await write_audit(
        session,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        company_id=user.company_id,
        actor_user_id=user.id,
        payload={"email": user.email},
    )
    await session.commit()
    return LoginResponse(
        access_token=token,
        user=AuthUserRead(
            id=user.id,
            company_id=user.company_id,
            email=user.email,
            full_name=user.full_name,
            roles=roles,
        ),
    )
