# app/crud/quiz_answer_crud.py
from datetime import datetime
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.auth.admin import user_required
from app.auth.utils import force_submit_attempt
from app.db import get_session
from app.models.quiz import QuizAnswer, QuizAttempt, Question, Option
from app.models.user import User
from app.schemas.quiz_schema import QuizAnswerBase
from sqlalchemy.orm import selectinload

async def create_quiz_answer(
    session: Annotated[AsyncSession, Depends(get_session)],
    attempt_id: int,
    question_id: int,
    option_id: int,
    user: User = Depends(user_required)
):
    # Ensure attempt exists
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Ensure question exists
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Ensure option exists
    option = await session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    answer = QuizAnswer(
        attempt_id=attempt_id,
        question_id=question_id,
        selected_option_id=option_id
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    return answer


async def get_answers_by_attempt(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    result = await session.exec(
        select(QuizAnswer).where(QuizAnswer.attempt_id == attempt_id)
    )
    return result.all()

#Save/update answer

async def save_or_update_answer(
    session: AsyncSession,
    attempt_id: int,
    answer: QuizAnswerBase
) -> QuizAnswer:
    attempt = await session.get(
        QuizAttempt,
        attempt_id,
        options=[selectinload(QuizAttempt.quiz)]
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # ✅ Deadline check
    if attempt.deadline and datetime.utcnow() > attempt.deadline:
        await force_submit_attempt(session, attempt)
        raise HTTPException(status_code=400, detail="Time is up! Attempt auto-submitted.")

    result = await session.exec(
        select(QuizAnswer).where(
            QuizAnswer.attempt_id == attempt_id,
            QuizAnswer.question_id == answer.question_id
        )
    )
    db_answer = result.one_or_none()

    if db_answer:
        db_answer.selected_option_id = answer.selected_option_id
    else:
        db_answer = QuizAnswer(
            attempt_id=attempt_id,
            question_id=answer.question_id,
            selected_option_id=answer.selected_option_id,
        )
        session.add(db_answer)

    try:
        await session.commit()
        await session.refresh(db_answer)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save answer: {e}")

    return db_answer

