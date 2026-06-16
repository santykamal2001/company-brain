"""
JWT auth + SSO (SAML 2.0 / OIDC) endpoints.
JWT is the default for local/dev. SSO is enabled via SSO_ENABLED=true.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import User
from access_control.rbac import acl_context_from_user
from config import get_settings
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_token(user_id: str, expires_delta: timedelta) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(days=settings.refresh_token_expire_days))


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = (
        request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        or request.cookies.get("access_token")
    )
    if not token:
        raise credentials_exc

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        "access_token", access_token, httponly=True, samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        "refresh_token", refresh_token, httponly=True, samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return response


@router.post("/refresh")
async def refresh(
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(str(user.id))
    response = JSONResponse({"access_token": new_access, "token_type": "bearer"})
    response.set_cookie("access_token", new_access, httponly=True, samesite="lax",
                        max_age=settings.access_token_expire_minutes * 60)
    return response


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse({"message": "logged out"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response


@router.get("/me")
async def me(user: CurrentUser) -> dict:
    dept = user.department.name if user.department else None
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role.value,
        "department": dept,
    }
