from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.models.quiz import Option
from app.models.user import User
from app.schemas.quiz_schema import OptionCreate,OptionUpdate

async def get_all_options(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    result = await session.exec(select(Option))
    return result.all()

async def get_option_by_id(session: Annotated[AsyncSession, Depends(get_session)], option_id: int,user: User = Depends(user_required)):
    option = await session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="option not found")
    return option

async def create_option(session: Annotated[AsyncSession, Depends(get_session)], option_data: OptionCreate,admin: User = Depends(admin_required)):
    option = Option.model_validate(option_data)
    session.add(option)
    await session.commit()
    await session.refresh(option)
    return option

async def update_option(session: Annotated[AsyncSession, Depends(get_session)], option_id: int, option_data:OptionUpdate,admin: User = Depends(admin_required)):
    option = await session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="option not found")
    update_data = option_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(option, key, value)
    session.add(option)
    await session.commit()
    await session.refresh(option)
    return option

async def delete_option(session: Annotated[AsyncSession, Depends(get_session)], option_id: int,admin: User = Depends(admin_required)):
    option = await session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="option not found")
    await session.delete(option)
    await session.commit()
    return option
