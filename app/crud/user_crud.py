from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.auth.utils import get_password_hash
from app.db import get_session
from app.models.user import Role, User
from app.schemas.user_schema import UserCreate, UserUpdate
from sqlalchemy.exc import SQLAlchemyError
import logging
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
   

async def get_all_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: User = Depends(admin_required)
):
    result = await session.exec(select(User).options(selectinload(User.role)))
    user = result.all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "role": u.role.name if u.role else "unknown",
            "email": u.email,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None
        }
        for u in user
    ]
    
async def signup_student(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_data: UserCreate,
):
    # ✅ Check if email already exists
    result = await session.exec(select(User).where(User.email == user_data.email))
    existing_user = result.one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ Find the "student" role
    result = await session.exec(select(Role).where(Role.name == "student"))
    student_role = result.one_or_none()
    if not student_role:
        raise HTTPException(status_code=404, detail="Role not found")

    # ✅ Create new user
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role_id=student_role.id,
    )
    session.add(db_user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")

    await session.refresh(db_user)

    # Reload with role
    stmt = select(User).options(selectinload(User.role)).where(User.id == db_user.id)
    result = await session.exec(stmt)
    db_user = result.one()

    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role.name if db_user.role else None,
        "created_at": db_user.created_at,
        "updated_at": db_user.updated_at,
    }

async def get_user_by_id(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int,
    user: User = Depends(user_required)
):
    stmt = select(User).options(selectinload(User.role))
    result = await session.exec(stmt)
    db_user = result.one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only admins can see others' profiles
    if user.role.name != "admin" and user.id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to view other users")

    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role.name if db_user.role else "student",
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
        "updated_at": db_user.updated_at.isoformat() if db_user.updated_at else None
    }

async def create_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_data: UserCreate,
    user: User = Depends(user_required)
):
    # find the "student" role
    result = await session.exec(select(Role).where(Role.name == "student"))
    student_role = result.one_or_none()
    if not student_role:
        raise HTTPException(status_code=404, detail="Role not found")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role_id=student_role.id
    )
    session.add(db_user)
    await session.commit()

    # reload with role eagerly loaded
    stmt = select(User).options(selectinload(User.role)).where(User.id == db_user.id)
    result = await session.exec(stmt)
    db_user = result.one()

    return {
        "id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role.name if db_user.role else "student",
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
        "updated_at": db_user.updated_at.isoformat() if db_user.updated_at else None,
    }

async def update_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int,
    data: UserUpdate,
    user: User = Depends(user_required)
):
    result = await session.exec(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.role))  # eager load role
    )
    db_user = result.one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = data.model_dump(exclude_unset=True)

    if "password" in user_data:
        db_user.password_hash = get_password_hash(user_data.pop("password"))

    for key, value in user_data.items():
        setattr(db_user, key, value)

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.name if user.role else "unknown",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }

async def delete_user(
   session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int,
    admin: User = Depends(admin_required)
    
):
    # Load user with role eagerly
    result = await session.exec(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == user_id)
    )
    db_user = result.one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await session.delete(db_user)
    await session.commit()

    # return dict to avoid serialization issues
    return {
            "id": str(db_user.id),
            "username": db_user.username,
            "email": db_user.email,
            "role": db_user.role.name if db_user.role else "unknown",
            "created_at": db_user.created_at.isoformat() if db_user.created_at else None,
            "updated_at": db_user.updated_at.isoformat() if db_user.updated_at else None,
        }



