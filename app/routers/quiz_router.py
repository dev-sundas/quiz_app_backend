from typing import Annotated, List
from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.crud.quiz_crud import (
    export_quiz_template, get_all_quizzes, get_quiz_by_id, create_quiz, get_quiz_with_options, get_user_quiz_history, import_quiz, update_quiz, delete_quiz
)
from app.models.user import User
from app.schemas.quiz_schema import QuizAttemptRead, QuizCreate, QuizHistoryRead, QuizRead, QuizUpdate, QuizWithOptions

quiz_router = APIRouter(prefix="/quiz", tags=["Quizes"])

@quiz_router.get("/", response_model=list[QuizRead])
async def list_quizzes(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    return await get_all_quizzes(session,user)

@quiz_router.get("/my-history", response_model=list[QuizHistoryRead])
async def my_quiz_history(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(user_required),
):
    return await get_user_quiz_history(
        session=session,
        user_id=current_user.id,
        current_user=current_user,
    )

@quiz_router.get("/export-quiz-template")
async def get_export_quiz():
    return await export_quiz_template()
@quiz_router.post("/import-quiz")
async def create_import_quiz(
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[User, Depends(admin_required)],  # 👈 Explicit
    file: UploadFile = File(...),
):    
    return await import_quiz(session, admin, file)



@quiz_router.get("/{quiz_id}", response_model=QuizRead)
async def get_quiz(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int,user: User = Depends(user_required)):
    return await get_quiz_by_id(session, quiz_id,user)

@quiz_router.post("/Create", response_model=QuizRead)
async def add_quiz(session: Annotated[AsyncSession, Depends(get_session)], quiz_data: QuizCreate,admin: User = Depends(admin_required)):
    return await create_quiz(session, quiz_data,admin)

@quiz_router.put("/Update/{quiz_id}", response_model=QuizRead)
async def edit_quiz(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int, quiz_data: QuizUpdate,admin: User = Depends(admin_required)):
    return await update_quiz(session, quiz_id, quiz_data,admin)

@quiz_router.delete("/Delete/{quiz_id}", response_model=QuizRead)
async def remove_quiz(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int,admin: User = Depends(admin_required)):
    return await delete_quiz(session, quiz_id,admin)


@quiz_router.get("/{quiz_id}/detail", response_model=QuizWithOptions)
async def detail_quiz_with_options(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int,user: User = Depends(user_required)):
    return await get_quiz_with_options(session, quiz_id,user)


