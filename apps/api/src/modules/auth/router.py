from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.rate_limit import check_rate_limit
from config.settings import Settings, get_settings
from infrastructure.db import get_db
from modules.auth.deps import AuthUser, get_current_user
from modules.auth.schemas import AuthUserRead, LoginRequest, LoginResponse
from modules.auth import service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{client}:{payload.email}", limit_per_minute=settings.rate_limit_per_minute)
    return await service.login(session, settings, payload)


@router.get("/me", response_model=AuthUserRead)
async def me(user: AuthUser | None = Depends(get_current_user)) -> AuthUserRead:
    if user is None:
        from common.errors import AppError

        raise AppError("Authentication required", status_code=401, code="auth_required")
    return AuthUserRead(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
    )
