"""Registration, login, refresh-token rotation, logout."""

import uuid

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models import User
from app.ratelimit import limiter
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_refresh_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=create_refresh_token(user.id, user.token_version),
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _token_response(response: Response, user: User) -> TokenOut:
    _set_refresh_cookie(response, user)
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(
        access_token=create_access_token(user.id, user.role.value),
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: Request, response: Response, body: RegisterIn, session: SessionDep
) -> TokenOut:
    user = User(email=body.email, password_hash=hash_password(body.password), locale=body.locale)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email_taken") from exc
    await session.refresh(user)
    return _token_response(response, user)


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request, response: Response, body: LoginIn, session: SessionDep
) -> TokenOut:
    user = await session.scalar(select(User).where(User.email == body.email))
    # verify_password runs argon2 even for unknown emails (constant-ish timing).
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await session.commit()
    return _token_response(response, user)


async def _user_from_refresh(request: Request, session: SessionDep) -> User:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    try:
        payload = decode_token(token, "refresh")
        user_id = uuid.UUID(payload["sub"])
        version = int(payload["ver"])
    except (TokenError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.token_version != version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


@router.post("/refresh", response_model=TokenOut)
@limiter.limit(settings.rate_limit_login)
async def refresh(request: Request, response: Response, session: SessionDep) -> TokenOut:
    user = await _user_from_refresh(request, session)
    return _token_response(response, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, session: SessionDep) -> None:
    try:
        user = await _user_from_refresh(request, session)
    except HTTPException:
        _clear_refresh_cookie(response)
        return
    # Invalidate every refresh token issued so far (all devices).
    user.token_version += 1
    await session.commit()
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
