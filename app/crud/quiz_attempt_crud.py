# app/crud/quiz_attempt_crud.py
from datetime import datetime, timedelta, timezone
from random import shuffle
from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.auth.utils import force_submit_attempt, serialize_attempt
from app.db import get_session
from app.models.quiz import Option, Question, QuizAnswer, QuizAttempt, Quiz, QuizResult
from app.models.user import User
from app.schemas.quiz_schema import QuizAnswerBase, QuizAnswerRead, QuizAttemptCreate, QuizAttemptRead, StudentStats
from sqlalchemy.orm import selectinload
from sqlalchemy import delete, func


async def create_quiz_attempt(
    session: AsyncSession,
    attempt_data: QuizAttemptCreate,
    current_user: User,
):
    # Load quiz with questions eagerly
    result = await session.exec(
    select(Quiz)
    .options(selectinload(Quiz.questions))
    .where(Quiz.id == attempt_data.quiz_id)
)
    quiz = result.one_or_none()  # or await result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Create attempt
    attempt = QuizAttempt(
        quiz_id=attempt_data.quiz_id,
        user_id=current_user.id,
        attempt_number=attempt_data.attempt_number
    )
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)

    return QuizAttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        user_id=attempt.user_id,
        answers=[],
        score=0,
        totalPoints=sum(q.marks for q in quiz.questions),  # questions now loaded
        timeSpent=0,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at
    )


async def get_quiz_attempt(
    session: AsyncSession,
    attempt_id: int,
    current_user: User = Depends(user_required),
):
    # Load the attempt with related answers, quiz, questions, options, and result
    attempt = await session.get(
        QuizAttempt,
        attempt_id,
        options=[
            selectinload(QuizAttempt.answers),  # load answers only
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(Question.options),
            selectinload(QuizAttempt.result)
        ]
)


    if not attempt or attempt.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Calculate time spent
    time_spent =(
        (attempt.submitted_at - attempt.started_at).total_seconds()
        if attempt.submitted_at else 0
    )

    # Use the result if it exists, otherwise default to 0 / total quiz marks
    score = attempt.result.score if attempt.result else 0
    total_points = attempt.result.max_score if attempt.result else sum(q.marks for q in attempt.quiz.questions)

    # Build answer list with correctness
    answers = []
    for a in attempt.answers:
        question = next((q for q in attempt.quiz.questions if q.id == a.question_id), None)
        correct_option_id = next((o.id for o in question.options if o.is_correct), None) if question else None
        answers.append(
            QuizAnswerRead(
                id=a.id,
                attempt_id=a.attempt_id,
                question_id=a.question_id,
                selected_option_id=a.selected_option_id,
                isCorrect=(a.selected_option_id == correct_option_id) if correct_option_id else None
            )
    )

    return QuizAttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        user_id=attempt.user_id,
        answers=answers,
        score=score,
        totalPoints=total_points,
        timeSpent=time_spent,
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at
    )


async def get_all_attempts(session: Annotated[AsyncSession, Depends(get_session)], admin: User = Depends(admin_required)):
    """
    Fetch all quiz attempts (admin-only).
    """
    result = await session.exec(select(QuizAttempt))
    return result.all()


async def get_attempt_by_id(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,user: User = Depends(user_required)):
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


async def get_user_attempts(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int,
    user: User = Depends(user_required),
):
    result = await session.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id)
        .options(selectinload(QuizAttempt.result))  # load result together
    )
    attempts = result.scalars().all()  # <-- fix here

    if not attempts:
        return StudentStats(totalAttempts=0, averageScore=0, bestScore=0, totalTimeSpent=0)

    completed = [a for a in attempts if a.submitted_at and a.result]

    if not completed:
        return StudentStats(totalAttempts=0, averageScore=0, bestScore=0, totalTimeSpent=0)

    total_score = sum(a.result.score for a in completed)
    total_points = sum(a.result.max_score for a in completed)
    avg = (total_score / total_points * 100) if total_points else 0
    best = max((a.result.score / a.result.max_score * 100) for a in completed)
    total_time = sum((a.submitted_at - a.started_at).total_seconds() for a in completed)

    return StudentStats(
        totalAttempts=len(completed),
        averageScore=round(avg, 2),
        bestScore=round(best, 2),
        totalTimeSpent=int(total_time),
    )


async def delete_attempt(session: Annotated[AsyncSession, Depends(get_session)], attempt_id: int,admin: User = Depends(admin_required)):
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    await session.delete(attempt)
    await session.commit()
    return attempt


async def get_or_create_quiz_attempt(
    quiz_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(user_required),
) -> QuizAttemptRead:
    # Load quiz with questions + options eagerly
    quiz = await session.get(
        Quiz,
        quiz_id,
        options=[selectinload(Quiz.questions).selectinload(Question.options)],
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # 1️⃣ Check for unfinished attempt
    result = await session.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.submitted_at.is_(None)
        )
        .order_by(QuizAttempt.attempt_number.desc())
        .with_for_update()
        .options(
            selectinload(QuizAttempt.answers),
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options)
        )
    )
    unfinished_attempt = result.scalars().first()

    if unfinished_attempt:

        # Generate shuffle_data if missing (for old attempts)
        if unfinished_attempt.shuffle_data is None and quiz.questions:
            question_ids = [q.id for q in quiz.questions]
            shuffle(question_ids)

            option_map = {}
            for q in quiz.questions:
                option_ids = [o.id for o in q.options]
                shuffle(option_ids)
                option_map[str(q.id)] = option_ids

            unfinished_attempt.shuffle_data = {
                "questions": question_ids,
                "options": option_map
            }
            session.add(unfinished_attempt)
            await session.commit()

        # Force-submit if deadline passed
        if unfinished_attempt.deadline and datetime.utcnow() > unfinished_attempt.deadline:
            unfinished_attempt = await force_submit_attempt(session, unfinished_attempt)

        # Return unfinished attempt
        if unfinished_attempt.submitted_at is None:
            return serialize_attempt(unfinished_attempt)

    # 2️⃣ Fetch all previous attempts
    result = await session.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id
        )
        .order_by(QuizAttempt.attempt_number.desc())
        .with_for_update()
        .options(
            selectinload(QuizAttempt.answers),
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options)
        )
    )
    all_attempts = result.scalars().all()
    last_attempt = all_attempts[0] if all_attempts else None

    # Enforce max_attempts
    if quiz.max_attempts is not None and len(all_attempts) >= quiz.max_attempts:
        raise HTTPException(
            status_code=403,
            detail=f"Maximum attempts reached ({quiz.max_attempts})"
        )

    if last_attempt:
        if last_attempt.submitted_at is None and last_attempt.deadline < datetime.utcnow():
            last_attempt = await force_submit_attempt(session, last_attempt)
        if last_attempt.submitted_at is None:
            return serialize_attempt(last_attempt)

    # 3️⃣ Create new attempt with shuffle
    question_ids = [q.id for q in quiz.questions]
    shuffle(question_ids)

    option_map = {}
    for q in quiz.questions:
        option_ids = [o.id for o in q.options]
        shuffle(option_ids)
        option_map[str(q.id)] = option_ids

    shuffle_data = {"questions": question_ids, "options": option_map}

    attempt_number = (last_attempt.attempt_number + 1) if last_attempt else 1
    new_attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        attempt_number=attempt_number,
        started_at=datetime.utcnow(),
        submitted_at=None,
        deadline=datetime.utcnow() + timedelta(minutes=quiz.total_time),
        shuffle_data=shuffle_data,
    )
    session.add(new_attempt)
    await session.flush()
    await session.commit()

    # Re-fetch attempt with eager-loading to avoid lazy load errors
    new_attempt = await session.get(
        QuizAttempt,
        new_attempt.id,
        options=[
            selectinload(QuizAttempt.answers),
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options)
        ]
    )

    print(f"✅ New attempt created: {new_attempt.id} with shuffle_data:", new_attempt.shuffle_data)
    return serialize_attempt(new_attempt)


async def submit_quiz_attempt(
    session: AsyncSession,
    attempt_id: int,
    answers_data: list[QuizAnswerBase],
    current_user: User,
):
    attempt = await session.get(
        QuizAttempt,
        attempt_id,
        options=[
            selectinload(QuizAttempt.answers),
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options),
            selectinload(QuizAttempt.result),
        ]
    )

    if not attempt or attempt.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # ✅ Deadline check
    if attempt.deadline and datetime.utcnow() > attempt.deadline:
        return await force_submit_attempt(session, attempt)

    # Delete previous answers
    if attempt.answers:
        await session.exec(delete(QuizAnswer).where(QuizAnswer.attempt_id == attempt.id))
        await session.commit()

    total_score = 0
    for ans in answers_data:
        question = next((q for q in attempt.quiz.questions if q.id == ans.question_id), None)
        if not question:
            continue

        selected_option = next((o for o in question.options if o.id == ans.selected_option_id), None)
        is_correct = selected_option.is_correct if selected_option else False
        if is_correct:
            total_score += question.marks

        quiz_answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option_id=ans.selected_option_id,
            is_correct=is_correct
        )
        session.add(quiz_answer)

    attempt.submitted_at = datetime.utcnow()
    await session.commit()

    result = QuizResult(
        attempt_id=attempt.id,
        score=total_score,
        max_score=sum(q.marks for q in attempt.quiz.questions),
        graded_at=datetime.utcnow()
    )
    session.add(result)
    await session.commit()
    await session.refresh(attempt)

    answers = []
    for a in attempt.answers:
        question = next((q for q in attempt.quiz.questions if q.id == a.question_id), None)
        correct_option_id = next((o.id for o in question.options if o.is_correct), None) if question else None
        answers.append(
            QuizAnswerRead(
                id=a.id,
                attempt_id=a.attempt_id,
                question_id=a.question_id,
                selected_option_id=a.selected_option_id,
                isCorrect=(a.selected_option_id == correct_option_id) if correct_option_id else None
            )
        )

        return QuizAttemptRead(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            user_id=attempt.user_id,
            answers=answers,
            score=total_score,
            totalPoints=sum(q.marks for q in attempt.quiz.questions),
            timeSpent=(attempt.submitted_at - attempt.started_at).total_seconds() if attempt.submitted_at else 0,
            started_at=attempt.started_at.replace(tzinfo=timezone.utc),        # ✅ FIXED
            submitted_at=(attempt.submitted_at.replace(tzinfo=timezone.utc)
                        if attempt.submitted_at else None),                  # ✅ FIXED
            deadline=attempt.deadline.replace(tzinfo=timezone.utc),            # ✅ FIXED
        )







