# app/routers/quiz_attempt_router.py
from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.crud.quiz_attempt_crud import create_quiz_attempt, get_all_attempts, delete_attempt, get_or_create_quiz_attempt, get_quiz_attempt, get_user_attempts, submit_quiz_attempt
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.schemas.quiz_schema import QuizAnswerBase, QuizAttemptCreate, QuizAttemptRead, StudentStats

quiz_attempt_router = APIRouter(prefix="/quiz_attempt", tags=["QuizAttempt"])


@quiz_attempt_router.get("/all_attempts",response_model=QuizAttemptRead)
async def fetch_all_attempt(session: Annotated[AsyncSession, Depends(get_session)], admin: User = Depends(admin_required)):
    result = await get_all_attempts(session=session,admin=admin)
    return result


@quiz_attempt_router.post("/", response_model=QuizAttemptRead)
async def start_attempt(
    attempt_data: QuizAttemptCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = Depends(user_required)
):
    print("Received attempt_data:", attempt_data)
    return await create_quiz_attempt(session, attempt_data, user)

@quiz_attempt_router.get("/{attempt_id}", response_model=QuizAttemptRead)
async def get_attempt(session: Annotated[AsyncSession, Depends(get_session)],attempt_id : int, current_user: User = Depends(user_required)):
    result = await get_quiz_attempt(session=session,attempt_id=attempt_id,current_user=current_user)
    return result

@quiz_attempt_router.post("/{quiz_id}/get-or-create-attempt", response_model=QuizAttemptRead)
async def fetch_or_create_attempt(session: Annotated[AsyncSession, Depends(get_session)],quiz_id : int, current_user: User = Depends(user_required)):
    """
    Retrieve the user's unfinished attempt for the given quiz.
    If no unfinished attempt exists, a new one is created automatically.
    """
    result = await get_or_create_quiz_attempt(session=session,quiz_id=quiz_id,current_user=current_user)
    return result

@quiz_attempt_router.get("/user/{user_id}/stats", response_model=StudentStats)
async def fetch_user_attempts(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int,
    user: User = Depends(user_required)
):
    return await get_user_attempts(session=session, user_id=user_id, user=user)


@quiz_attempt_router.delete("/Delete/{attempt_id}",response_model=QuizAttemptRead)
async def remove_attempt(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,admin: User = Depends(admin_required)):
    return await delete_attempt(session, attempt_id,admin)


@quiz_attempt_router.post("/submit/{attempt_id}", response_model=QuizAttemptRead)
async def submit_attempt(
    attempt_id: int,
    answers: list[QuizAnswerBase],
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = Depends(user_required)
):
    return await submit_quiz_attempt(session, attempt_id, answers, user)


# @quiz_attempt_router.get("/{attempt_id}",response_model=QuizAttemptRead)
# async def fetch_attempt(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
#     return await get_attempt_by_id(session, attempt_id,user)

