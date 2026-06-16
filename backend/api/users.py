from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import Department, RoleEnum, User
from api.auth import CurrentUser
from database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str
    password: str | None = None
    role: RoleEnum = RoleEnum.employee
    department_id: UUID | None = None
    project_ids: list[str] = []


class UpdateUserRequest(BaseModel):
    role: RoleEnum | None = None
    department_id: UUID | None = None
    project_ids: list[str] | None = None
    is_active: bool | None = None


def _require_admin(user: CurrentUser) -> CurrentUser:
    if user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@router.get("/")
async def list_users(
    admin: CurrentUser = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [_user_dict(u) for u in users]


@router.post("/", status_code=201)
async def create_user(
    body: CreateUserRequest,
    admin: CurrentUser = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = pwd_context.hash(body.password) if body.password else None
    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hashed,
        role=body.role,
        department_id=body.department_id,
        project_ids=body.project_ids,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    admin: CurrentUser = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        user.role = body.role
    if body.department_id is not None:
        user.department_id = body.department_id
    if body.project_ids is not None:
        user.project_ids = body.project_ids
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: UUID,
    admin: CurrentUser = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()


@router.get("/departments")
async def list_departments(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(select(Department).order_by(Department.name))
    depts = result.scalars().all()
    return [{"id": str(d.id), "name": d.name} for d in depts]


@router.post("/departments", status_code=201)
async def create_department(
    name: str,
    admin: CurrentUser = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    dept = Department(name=name)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return {"id": str(dept.id), "name": dept.name}


def _user_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role.value,
        "department_id": str(user.department_id) if user.department_id else None,
        "project_ids": user.project_ids,
        "sso_provider": user.sso_provider,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
