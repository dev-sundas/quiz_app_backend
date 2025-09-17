from typing import Annotated
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import APIRouter, Depends
from app.auth.admin import admin_required, user_required
from app.crud.question_crud import get_all_questions
from app.crud.quiz_attempt_crud import get_all_attempts
from app.crud.quiz_crud import get_all_quizzes
from app.crud.user_crud import create_user, delete_user, get_all_user, get_user_by_id, signup_student, update_my_profile, update_user
from app.db import get_session
from app.models.user import User
from app.schemas.user_schema  import UserCreate, UserRead, UserUpdate


user_router = APIRouter(prefix="/user",tags=["Users"])

@user_router.post("/signup",response_model=UserRead)
async def register_user(session: Annotated[AsyncSession, Depends(get_session)],user_data:UserCreate):
    user = await signup_student(session=session,user_data=user_data)
    return user

@user_router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: User = Depends(user_required)
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.name,  
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
    }

@user_router.put("/me/update")
async def updateMyprofile( data: UserUpdate,session: Annotated[AsyncSession, Depends(get_session)],user: User = Depends(user_required)):
    user = await update_my_profile(data=data,session=session,user=user)
    return user
@user_router.get("/admin/stats")
async def get_admin_stats(session: Annotated[AsyncSession, Depends(get_session)],admin: User = Depends(admin_required)):
    total_users = len(await get_all_user(session=session))
    total_quizzes = len(await get_all_quizzes(session=session,user=admin))
    total_attempts = len(await get_all_attempts(session=session,))
    total_questions = len(await get_all_questions(session=session))
    recent_attempts = (await get_all_attempts(session=session))[-5:]  # last 5 attempts

    return {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "total_questions": total_questions,
        "recent_attempts": recent_attempts,
    }


@user_router.get("/",response_model=list[UserRead])
async def list_users(session: Annotated[AsyncSession, Depends(get_session)],admin: User = Depends(admin_required)):
    user = await get_all_user(session=session,admin=admin)
    return user

@user_router.post("/Create",response_model=UserRead)
async def add_user(session: Annotated[AsyncSession, Depends(get_session)],user_data:UserCreate,user: User = Depends(user_required)):
    user = await create_user(session=session,user_data=user_data,user=user)
    return user


@user_router.get("/{user_id}",response_model = UserRead)
async def singal_user(session: Annotated[AsyncSession, Depends(get_session)],user_id: int,user: User = Depends(user_required)):
    user = await get_user_by_id(session=session,user_id = user_id,user=user)
    return user
    



@user_router.put("/Update/{user_id}",response_model=UserRead)
async def updateuser(session: Annotated[AsyncSession, Depends(get_session)],user_id: int, user_data:UserUpdate,user: User = Depends(user_required)):
    user = await update_user(session=session,user_id=user_id,data=user_data,user=user)
    return user 


@user_router.delete("/Delete/{user_id}",response_model=UserRead)
async def deleteuser(session: Annotated[AsyncSession, Depends(get_session)],user_id: int,admin: User = Depends(admin_required)):
    user = await delete_user(session=session,user_id=user_id,admin=admin)
    return user

