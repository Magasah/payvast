"""Registration, login (email or Telegram), refresh-token rotation, logout."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.deps import CurrentUser, SessionDep, is_admin
from app.models import User, UserRole
from app.ratelimit import limiter
from app.schemas.auth import LocaleIn, LoginIn, RegisterIn, TelegramLoginIn, TokenOut, UserOut
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.services.users import UpsertConflict, upsert_telegram_user
from app.telegram.initdata import InitDataError, verify_init_data

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


def user_out(user: User) -> UserOut:
    admin = is_admin(user)
    return UserOut(
        id=user.id,
        email=user.email,
        telegram_username=user.telegram_username,
        has_telegram=user.telegram_id is not None,
        role=UserRole.ADMIN if admin else UserRole.USER,
        is_admin=admin,
        locale=user.locale,
    )


def _token_response(response: Response, user: User) -> TokenOut:
    _set_refresh_cookie(response, user)
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(
        access_token=create_access_token(user.id, user.role.value),
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user=user_out(user),
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


_BAD_CREDENTIALS = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request, response: Response, body: LoginIn, session: SessionDep
) -> TokenOut:
    user = (
        await session.scalars(select(User).where(User.email == body.email).with_for_update())
    ).first()
    now = datetime.now(UTC)
    locked = (
        user is not None and user.login_locked_until is not None and (user.login_locked_until > now)
    )
    # verify_password runs argon2 even for unknown emails (constant-ish timing).
    ok = verify_password(user.password_hash if user else None, body.password)
    if user is None:
        raise _BAD_CREDENTIALS
    if locked or not ok:
        if not locked:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.failed_login_count = 0
                user.login_locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        await session.commit()
        # Same answer for locked, wrong password and unknown email: nothing to enumerate.
        raise _BAD_CREDENTIALS
    if not user.is_active or user.password_hash is None:
        await session.rollback()
        raise _BAD_CREDENTIALS
    user.failed_login_count = 0
    user.login_locked_until = None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    await session.commit()
    return _token_response(response, user)


@router.post("/telegram", response_model=TokenOut)
@limiter.limit(settings.rate_limit_telegram)
async def telegram_login(
    request: Request, response: Response, body: TelegramLoginIn, session: SessionDep
) -> TokenOut:
    """Sign in from inside the Telegram Mini App with signed initData."""
    try:
        tg = verify_init_data(
            body.init_data,
            settings.telegram_bot_token.get_secret_value(),
            settings.telegram_auth_max_age_seconds,
        )
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_telegram_data") from exc
    try:
        user = await upsert_telegram_user(session, tg.id, tg.username, tg.language_code)
    except UpsertConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="try_again") from exc
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="account_disabled")
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
@limiter.limit(settings.rate_limit_refresh)
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
    return user_out(user)


@router.patch("/me", response_model=UserOut)
async def update_me(body: LocaleIn, user: CurrentUser, session: SessionDep) -> UserOut:
    user.locale = body.locale
    await session.commit()
    return user_out(user)
