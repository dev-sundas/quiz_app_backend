from typing import Annotated
from fastapi import Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.auth.admin import admin_required, user_required
from app.db import get_session
from app.models.quiz import Question
from app.models.user import User
from sqlalchemy.orm import selectinload
from app.schemas.quiz_schema import QuestionCreate,QuestionUpdate

async def get_all_questions(session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    result = await session.exec(select(Question))
    return result.all()

async def get_question_by_id(session: Annotated[AsyncSession, Depends(get_session)], question_id: int,user: User = Depends(user_required)):
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="question not found")
    return question

async def create_question(session: Annotated[AsyncSession, Depends(get_session)], question_data: QuestionCreate,admin: User = Depends(admin_required)):
    question = Question.model_validate(question_data)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question

async def update_question(session: Annotated[AsyncSession, Depends(get_session)], question_id: int, question_data:QuestionUpdate,admin: User = Depends(admin_required)):
    question = await session.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="question not found")
    update_data = question_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question

async def delete_question(
    session: Annotated[AsyncSession, Depends(get_session)],
    question_id: int,
    admin: User = Depends(admin_required),
):
    question = await session.get(Question, question_id, options=[selectinload(Question.options)])
    if not question:
        raise HTTPException(status_code=404, detail="question not found")

    # Delete related options first
    for option in question.options:
        await session.delete(option)

    # Now delete the question
    await session.delete(question)
    await session.commit()
    return question

