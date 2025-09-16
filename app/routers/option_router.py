from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.crud.option_crud import (
    get_all_options, get_option_by_id, create_option, update_option, delete_option
)
from app.models.user import User
from app.schemas.quiz_schema import OptionCreate, OptionRead, OptionUpdate

option_router = APIRouter(prefix="/option", tags=["Options"])

@option_router.get("/", response_model=list[OptionRead])
async def list_optiones(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    return await get_all_options(session,user)

@option_router.get("/{option_id}", response_model=OptionRead)
async def get_option(session: Annotated[AsyncSession, Depends(get_session)], option_id: int,user: User = Depends(user_required)):
    return await get_option_by_id(session, option_id,user)

@option_router.post("/Create", response_model=OptionRead)
async def add_option(session: Annotated[AsyncSession, Depends(get_session)], option_data: OptionCreate,admin: User = Depends(admin_required)):
    return await create_option(session, option_data,admin)

@option_router.put("/Update/{option_id}", response_model=OptionRead)
async def edit_option(session: Annotated[AsyncSession, Depends(get_session)], option_id: int, option_data: OptionUpdate,admin: User = Depends(admin_required)):
    return await update_option(session, option_id, option_data,admin)

@option_router.delete("/Delete/{option_id}", response_model=OptionRead)
async def remove_option(session: Annotated[AsyncSession, Depends(get_session)], option_id: int,admin: User = Depends(admin_required)):
    return await delete_option(session, option_id,admin)
