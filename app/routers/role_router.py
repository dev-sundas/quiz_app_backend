from typing import Annotated
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends
from app.auth.admin import admin_required, user_required
from app.crud.role_crud import create_role, delete_role, get_all_role, get_role_by_id, update_role
from app.db import get_session
from app.models.user import User
from app.schemas.user_schema  import RoleCreate, RoleRead, RoleUpdate


role_router = APIRouter(prefix="/role",tags=["Roles"])


@role_router.get("/",response_model=list[RoleRead])
async def list_role(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    role = await get_all_role(session=session)
    return role
    
@role_router.get("/{role_id}",response_model = RoleRead)
async def singal_role(session: Annotated[AsyncSession, Depends(get_session)],role_id: int,user: User = Depends(user_required)):
    role = await get_role_by_id(session=session,role_id = role_id,user=user)
    return role
    

@role_router.post("/Create",response_model=RoleRead)
async def add_role(session: Annotated[AsyncSession, Depends(get_session)],role_data:RoleCreate,admin: User = Depends(admin_required)):
    role = await create_role(session=session,role_data=role_data,admin=admin)
    return role

@role_router.put("/Update/{role_id}",response_model=RoleRead)
async def updaterole(session: Annotated[AsyncSession, Depends(get_session)],role_id: int, role_data:RoleUpdate,admin: User = Depends(admin_required)):
    role = await update_role(session=session,role_id=role_id,data=role_data,admin=admin)
    return role

@role_router.delete("/Delete/{role_id}",response_model=RoleRead)
async def deleterole(session: Annotated[AsyncSession, Depends(get_session)],role_id: int,admin: User = Depends(admin_required)):
    role = await delete_role(session=session,role_id=role_id,admin=admin)
    return role
