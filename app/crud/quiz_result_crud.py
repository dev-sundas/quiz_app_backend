# app/crud/quiz_result_crud.py
from sqlalchemy.orm import selectinload
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import user_required
from app.db import get_session
from app.models.quiz import Quiz, QuizResult, QuizAttempt, QuizAnswer, Option
from app.models.user import User

async def calculate_and_save_result(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Fetch all answers for this attempt
    answers_result = await session.exec(select(QuizAnswer).where(QuizAnswer.attempt_id == attempt_id))
    answers = answers_result.all()

    score = 0
    max_score = 0

    for ans in answers:
        option = await session.get(Option, ans.selected_option_id)
        if option and option.is_correct:
            score += 1
        max_score += 1

    # Save result
    result = QuizResult(attempt_id=attempt_id, score=score, max_score=max_score)
    session.add(result)
    await session.commit()
    await session.refresh(result)
    return result


async def get_result_by_attempt(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    result = await session.execute(select(QuizResult).where(QuizResult.attempt_id == attempt_id))
    return result.scalar_one_or_none()

async def get_all_results(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    stmt = (
         select(QuizResult, QuizAttempt, User,Quiz)
        .join(QuizAttempt, QuizAttempt.id == QuizResult.attempt_id)
        .join(User, User.id == QuizAttempt.user_id)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
    )
    results = await session.exec(stmt)
    return [
        {
            "id": qr.id,
            "score": qr.score,
            "max_score": qr.max_score,
            "graded_at": qr.graded_at,
            "attempt_id": qa.id,
            "quiz_id": qa.quiz_id,
            "quiz_title":q.title,
            "started_at": qa.started_at,
            "completed_at": qa.submitted_at,
            "student": {
                "id": u.id,
                "username": u.username,
                "email": u.email
            }
        }
        for qr, qa, u,q in results.all()
    ]       