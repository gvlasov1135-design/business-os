import secrets
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.errors import AppError
from common.security import decode_access_token
from config.settings import Settings, get_settings
from infrastructure.db import get_db
from modules.identity.models import User


@dataclass
class AuthUser:
    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]


async def _load_user_from_authorization(
    authorization: str | None,
    session: AsyncSession,
    settings: Settings,
    *,
    required: bool,
) -> AuthUser | None:
    if not authorization:
        if required:
            raise AppError("Authentication required", status_code=401, code="auth_required")
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError("Invalid authorization header", status_code=401, code="invalid_auth_header")

    payload = decode_access_token(settings, token)
    user_id = uuid.UUID(str(payload["sub"]))
    user = await session.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise AppError("User not found or inactive", status_code=401, code="user_inactive")

    return AuthUser(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        full_name=user.full_name,
        roles=[role.code for role in user.roles],
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthUser | None:
    return await _load_user_from_authorization(
        authorization,
        session,
        settings,
        required=settings.auth_required,
    )


def require_roles(*allowed: str):
    async def _dependency(user: AuthUser | None = Depends(get_current_user)) -> AuthUser | None:
        settings = get_settings()
        if not settings.auth_required:
            return user
        if user is None:
            raise AppError("Authentication required", status_code=401, code="auth_required")
        if "admin" in user.roles:
            return user
        if allowed and not any(role in user.roles for role in allowed):
            raise AppError("Forbidden", status_code=403, code="forbidden")
        return user

    return _dependency


def require_roles_or_worker(*allowed: str):
    async def _dependency(
        authorization: str | None = Header(default=None),
        x_worker_key: str | None = Header(default=None),
        session: AsyncSession = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ) -> AuthUser | None:
        if x_worker_key and secrets.compare_digest(x_worker_key, settings.worker_secret):
            return None

        user = await _load_user_from_authorization(
            authorization,
            session,
            settings,
            required=settings.auth_required,
        )
        if not settings.auth_required:
            return user
        if user is None:
            raise AppError("Authentication required", status_code=401, code="auth_required")
        if "admin" in user.roles:
            return user
        if allowed and not any(role in user.roles for role in allowed):
            raise AppError("Forbidden", status_code=403, code="forbidden")
        return user

    return _dependency
