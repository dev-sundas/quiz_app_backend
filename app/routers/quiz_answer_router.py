# app/routers/quiz_answer_router.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import user_required
from app.db import get_session
from app.crud.quiz_answer_crud import create_quiz_answer, get_answers_by_attempt, save_or_update_answer
from app.models.quiz import Question, Quiz, QuizAttempt
from app.models.user import User
from app.schemas.quiz_schema import QuizAnswerRead, QuizAttemptRead
from app.schemas.quiz_schema import QuizAnswerBase
from app.crud.quiz_attempt_crud import get_quiz_attempt
from sqlalchemy.orm import selectinload

quiz_answer_router = APIRouter(prefix="/quiz_answer", tags=["Quizanswer"])

@quiz_answer_router.post("/")
async def give_answer(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int, question_id: int, option_id: int,user: User = Depends(user_required)):
    return await create_quiz_answer(session, attempt_id, question_id,option_id,user)

@quiz_answer_router.post("/{attempt_id}/save-answer", response_model=QuizAttemptRead)
async def save_answer(
    attempt_id: int,
    answer: QuizAnswerBase,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: User = Depends(user_required)
):
    # Load attempt async-safe
    result = await session.exec(
        select(QuizAttempt)
        .where(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == current_user.id
        )
        .options(
            selectinload(QuizAttempt.answers),
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(Question.options),
            selectinload(QuizAttempt.result)
        )
    )
    attempt_orm = result.first()

    if not attempt_orm:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Save or update the answer
    await save_or_update_answer(session, attempt_id, answer)

    # Return updated attempt
    return await get_quiz_attempt(session, attempt_id, current_user)

@quiz_answer_router.get("/{attempt_id}")
async def fetch_answer(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    return await get_answers_by_attempt(session, attempt_id,user)

