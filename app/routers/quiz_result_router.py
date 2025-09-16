# app/routers/quiz_result_router.py
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import user_required
from app.db import get_session
from app.crud.quiz_result_crud import calculate_and_save_result, get_all_results,get_result_by_attempt
from app.models.user import User

quiz_result_router = APIRouter(prefix="/quiz_result", tags=["Quizresult"])

@quiz_result_router.post("/submitt_result")
async def add_result(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    return await calculate_and_save_result(session, attempt_id,user)


@quiz_result_router.get("/{attempt_id}")
async def fetch_result(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    return await get_result_by_attempt(session, attempt_id,user)

@quiz_result_router.get("/")
async def fetch_all_result(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    return await get_all_results(session)
