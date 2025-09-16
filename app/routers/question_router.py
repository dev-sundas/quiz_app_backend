from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.crud.question_crud import (
    get_all_questions, get_question_by_id, create_question, update_question, delete_question
)
from app.models.user import User
from app.schemas.quiz_schema import QuestionCreate, QuestionRead, QuestionUpdate

question_router = APIRouter(prefix="/question", tags=["Questions"])

@question_router.get("/", response_model=list[QuestionRead])
async def list_questions(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    return await get_all_questions(session,user)

@question_router.get("/{question_id}", response_model=QuestionRead)
async def get_question(session: Annotated[AsyncSession, Depends(get_session)], question_id: int,user: User = Depends(user_required)):
    return await get_question_by_id(session, question_id,user)

@question_router.post("/Create", response_model=QuestionRead)
async def add_question(session: Annotated[AsyncSession, Depends(get_session)], question_data: QuestionCreate,admin: User = Depends(admin_required)):
    return await create_question(session, question_data,admin)

@question_router.put("/Update/{question_id}", response_model=QuestionRead)
async def edit_question(session: Annotated[AsyncSession, Depends(get_session)], question_id: int, question_data: QuestionUpdate,admin: User = Depends(admin_required)):
    return await update_question(session, question_id, question_data,admin)

@question_router.delete("/Delete/{question_id}", response_model=QuestionRead)
async def remove_question(session: Annotated[AsyncSession, Depends(get_session)], question_id: int,admin: User = Depends(admin_required)):
    return await delete_question(session, question_id,admin)
