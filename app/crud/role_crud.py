from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.models.user import Role, User
from app.schemas.user_schema import RoleCreate, RoleUpdate
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
   

async def get_all_role(session: Annotated[AsyncSession, Depends(get_session)]):
    result = await session.exec(
        select(Role).options(selectinload(Role.users)) 
    )
    role = result.all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "users": [{"id": u.id, "username": u.username} for u in r.users] if r.users else []
        }
        for r in role
    ]

async def get_role_by_id(session:Annotated[AsyncSession,Depends(get_session)],role_id:int,user: User = Depends(user_required)):
    stmt = select(Role).options(selectinload(Role).where(Role.id == role_id))
    result  = await session.exec(stmt)
    role = result.one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "users": [{"id": u.id, "username": u.username} for u in role.users] if role.users else []
    }

async def create_role(
    session: Annotated[AsyncSession, Depends(get_session)], 
    role_data: RoleCreate, 
    admin: User = Depends(admin_required)
):
    try:
        db_role = Role.model_validate(role_data)
        session.add(db_role)
        await session.commit()  

        # Reload role with users eagerly loaded
        result = await session.exec(
            select(Role)
            .where(Role.id == db_role.id)
            .options(selectinload(Role.users))
        )
        db_role = result.first()

        return {
            "id": db_role.id,
            "name": db_role.name,
            "description": db_role.description,
            "users": [
                {"id": u.id, "username": u.username} for u in db_role.users
            ] if db_role.users else []
        }

    except SQLAlchemyError as error:
        await session.rollback()
        raise error
    except Exception as e:
        await session.rollback()
        raise e

async def update_role(
    session: Annotated[AsyncSession, Depends(get_session)],
    role_id: int,
    data: RoleUpdate,
    admin: User = Depends(admin_required)
):
    result = await session.exec(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.users))  # eager load users if relationship exists
    )
    db_role = result.one_or_none()

    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")

    role_data = data.model_dump(exclude_unset=True)
    for key, value in role_data.items():
        setattr(db_role, key, value)
    session.add(db_role)
    await session.commit()
    await session.refresh(db_role)
    return {
        "id": db_role.id,
        "name": db_role.name,
        "description": db_role.description,
        "users": [{"id": u.id, "username": u.username} for u in db_role.users] if db_role.users else []
    }

async def delete_role(session:Annotated[AsyncSession,Depends(get_session)],role_id:int,admin: User = Depends(admin_required)):
   stmt = select(Role).where(Role.id == role_id).options(selectinload(Role.users))
   role = await session.exec(stmt)
   role = role.one_or_none()
   if not role :
       raise HTTPException(status_code=404, detail="role not found")
   await session.delete(role)
   await session.commit()
   return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "users": [{"id": u.id, "username": u.username} for u in role.users] if role.users else []
    }
