import math
from typing import Annotated, List
from fastapi import Depends, File, HTTPException, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.models.quiz import Option, Question, Quiz, QuizAttempt
from app.models.user import User
from app.schemas.quiz_schema import QuizAttemptSummary, QuizCreate, QuizHistoryRead, QuizUpdate
from sqlalchemy.orm import selectinload
import pandas as pd
from fastapi.responses import StreamingResponse
import io

async def get_all_quizzes(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = Depends(user_required)
):
    stmt = select(Quiz).options(
        selectinload(Quiz.questions),
        selectinload(Quiz.attempts)
    )
    result = await session.exec(stmt)
    quizzes = result.all()

    # Return as dicts with attempts_made included
    return [
        {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "total_time": quiz.total_time,
            # "question_count": len(quiz.questions),
            "max_attempts": quiz.max_attempts,
            "is_active": quiz.is_active,
            "attempts_made": sum(1 for a in quiz.attempts if a.user_id == user.id),
            "created_at": quiz.created_at,
            "updated_at": quiz.updated_at,
            "questions": [  # <-- serialize questions
                {
                    "id": q.id,
                    "quiz_id": q.quiz_id,  # <-- add this
                    "text": q.text,
                    "marks": q.marks,
                    # add any other fields you need
                }
                for q in quiz.questions
            ]
        }
        for quiz in quizzes
    ]

async def get_quiz_by_id(
    session: Annotated[AsyncSession, Depends(get_session)],
    quiz_id: int,
    user: User = Depends(user_required),
):
    result = await session.exec(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(Question.options)  # ✅ eager load questions + options
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.one_or_none()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # ✅ Build response object
    quiz_data = {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "total_time": quiz.total_time,
        "created_at": quiz.created_at,
        "updated_at": quiz.updated_at,
        "questions": [],
    }

    for q in quiz.questions:
        # options for each question
        options = [
            {
                "id": o.id,
                "text": o.text,
                "is_correct": o.is_correct,  # ⚠️ includes correct answer info
            }
            for o in q.options
        ]

        # find index of correct answer
        correct_index = next((i for i, o in enumerate(q.options) if o.is_correct), None)

        quiz_data["questions"].append({
            "id": q.id,
            "quiz_id": q.quiz_id,
            "text": q.text,
            "marks": q.marks,
            "type": "multiple-choice",
            "options": options,
            "correctAnswer": correct_index,  # ✅ frontend expects this
        })

    return quiz_data

async def create_quiz(
    session: Annotated[AsyncSession, Depends(get_session)],
    quiz_data: QuizCreate,
    admin: User = Depends(admin_required)
):
    # Create quiz from Pydantic data
    quiz = Quiz.model_validate(quiz_data)

    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)

    # Reload the quiz with questions eagerly loaded
    result = await session.exec(
        select(Quiz)
        .where(Quiz.id == quiz.id)
        .options(selectinload(Quiz.questions))
    )
    quiz = result.one_or_none()  # ✅ use this instead of scalars().first()

    return quiz

async def update_quiz(
    session: Annotated[AsyncSession, Depends(get_session)],
    quiz_id: int,
    quiz_data: QuizUpdate,
    admin: User = Depends(admin_required)
):
    # Eager-load questions to avoid lazy-load errors
    result = await session.execute(
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions))
    )
    quiz = result.scalars().first()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Update only provided fields
    update_data = quiz_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(quiz, key, value)
    
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    
    # Return a Pydantic schema to avoid triggering lazy-load
    return quiz

async def delete_quiz(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int,admin: User = Depends(admin_required)):
    quiz = await session.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await session.delete(quiz)
    await session.commit()
    return quiz

async def get_quiz_with_options(session: Annotated[AsyncSession, Depends(get_session)], quiz_id: int, user: User):
    result = await session.exec(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(Question.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

async def get_user_quiz_history(
    session: AsyncSession,
    user_id: int,
    current_user: User,
) -> List[QuizHistoryRead]:
    # Fetch all submitted attempts for the user
    result = await session.exec(
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None)  # ✅ only include submitted attempts
        )
        .options(
            selectinload(QuizAttempt.quiz)
            .selectinload(Quiz.questions)
            .selectinload(Question.options),
            selectinload(QuizAttempt.result),
            selectinload(QuizAttempt.answers),
        )
    )

    attempts = result.all()

    # Aggregate per quiz
    quizzes: dict[int, dict] = {}

    for attempt in attempts:
        quiz = attempt.quiz
        if quiz.id not in quizzes:
            quizzes[quiz.id] = {
                "quiz_title": quiz.title,
                "totalQuestions": len(quiz.questions),
                "attempts_data": [],
                "totalTimeSpent": 0.0,
                "scores": [],
            }

        # Count correct and wrong answers
        correct_count = 0
        wrong_count = 0
        for a in attempt.answers:
            question = next((q for q in quiz.questions if q.id == a.question_id), None)
            correct_option_id = next((o.id for o in question.options if o.is_correct), None) if question else None
            if correct_option_id and a.selected_option_id == correct_option_id:
                correct_count += 1
            else:
                wrong_count += 1

        # Score and time for this attempt
        score = float(attempt.result.score) if attempt.result else 0.0
        total_points = float(attempt.result.max_score) if attempt.result else sum(q.marks for q in quiz.questions)
        time_spent = (
            (attempt.submitted_at - attempt.started_at).total_seconds()
            if attempt.submitted_at else 0.0
        )

        quizzes[quiz.id]["attempts_data"].append(
            QuizAttemptSummary(
                attempt_number=attempt.attempt_number,  # ✅ use DB value
                score=score,
                totalPoints=total_points,
                timeSpent=time_spent,
                correctAnswers=correct_count,
                wrongAnswers=wrong_count,
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
                # id=f"{quiz.id}-{attempt.attempt_number}",  # ✅ unique key for frontend
                id=attempt.id,  # real integer
            )
        )

        quizzes[quiz.id]["totalTimeSpent"] += time_spent
        quizzes[quiz.id]["scores"].append(score)

    # Build response
    history: List[QuizHistoryRead] = []
    for quiz_id, data in quizzes.items():
        scores = data["scores"]
        total_attempts = len(scores)
        avg_score = round(sum(scores) / total_attempts, 2) if total_attempts else 0.0
        best_score = max(scores) if scores else 0.0
        total_time_seconds = int(data["totalTimeSpent"])

        history.append(
            QuizHistoryRead(
                quiz_id=quiz_id,
                quiz_title=data["quiz_title"],
                totalAttempts=total_attempts,
                averageScore=avg_score,
                bestScore=best_score,
                totalTimeSpent=total_time_seconds,
                totalQuestions=data["totalQuestions"],
                attempts=data["attempts_data"],
            )
        )

    return history

async def import_quiz(
    session: AsyncSession,
    admin: User,
    file: UploadFile,
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Invalid file format. Upload an Excel file.")

    # Read Excel with pandas
    df = pd.read_excel(file.file)

    # Validate mandatory columns
    required_cols = ["Quiz Title", "Quiz Description", "Time Limit", "Question Text", 
                     "Option A", "Option B", "Option C", "Option D", "Correct Option"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")

    # Extract quiz info from first row
    quiz_title = df.iloc[0]["Quiz Title"]
    description = df.iloc[0]["Quiz Description"]
    total_time = int(df.iloc[0]["Time Limit"])

    # Handle optional Max Attempts
    max_attempts = None
    if "Max Attempts" in df.columns:
        val = df.iloc[0]["Max Attempts"]
        if pd.notna(val):
            max_attempts = int(val)

    # Create quiz
    quiz = Quiz(
        title=quiz_title,
        description=description,
        total_time=total_time,
        max_attempts=max_attempts
    )
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)

    # Add questions + options
    for _, row in df.iterrows():
        # Handle optional Marks
        marks = 1
        if "Marks" in df.columns and pd.notna(row["Marks"]):
            marks = int(row["Marks"])

        question = Question(
            quiz_id=quiz.id,
            text=row["Question Text"],
            marks=marks
        )
        session.add(question)
        await session.commit()
        await session.refresh(question)

        # Add options
        for idx, col in enumerate(["Option A", "Option B", "Option C", "Option D"]):
            text = str(row[col]) if pd.notna(row[col]) else ""
            option = Option(
                question_id=question.id,
                text=text,
                is_correct=(chr(65 + idx) == str(row["Correct Option"]).strip())
            )
            session.add(option)
        await session.commit()

    return {
        "message": f"Quiz '{quiz_title}' imported successfully",
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "total_time": quiz.total_time,
            "max_attempts": quiz.max_attempts,
            "is_active": quiz.is_active,
            "created_at": str(quiz.created_at),
            "question_count": len(df),
        },
    }

async def export_quiz_template():
    # Define columns (including optional ones)
    columns = [
        "Quiz Title", "Quiz Description", "Time Limit", "Max Attempts",
        "Question Text", "Marks", "Option A", "Option B", "Option C", "Option D", "Correct Option"
    ]

    # Create empty DataFrame with headers only
    df = pd.DataFrame(columns=columns)

    # Optionally: add a sample row for guidance
    df.loc[0] = [
        "Sample Quiz",
        "This is a sample description",
        30,
        3,
        "What is 2+2?",
        1,
        "3", "4", "5", "6",
        "B"
    ]

    # Save to BytesIO
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="QuizTemplate")
    output.seek(0)

    # Return as downloadable file
    headers = {"Content-Disposition": "attachment; filename=quiz_template.xlsx"}
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
