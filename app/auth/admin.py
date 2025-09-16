
from sqlmodel import select
from app.auth.deps import get_current_user
from app.auth.utils import get_password_hash
from app.db import AsyncSessionLocal
from app.models.user import Role, User
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User


async def create_admin():
    async with AsyncSessionLocal() as session:
        # Ensure admin role exists
        result = await session.exec(select(Role).where(Role.name == "admin"))
        admin_role = result.first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator role")
            session.add(admin_role)
            await session.commit()
            await session.refresh(admin_role)

        # Ensure admin user exists
        result = await session.exec(select(User).where(User.username == "admin"))
        admin = result.first()
        if not admin:
            new_admin = User(
                username="admin",
                email="admin@gmail.com",
                password_hash=get_password_hash("admin123"),
                role_id=admin_role.id,
            )
            session.add(new_admin)
            await session.commit()
            print("Admin user created ✅")



def admin_required(user: User = Depends(get_current_user)):
    if user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only!"
        )
    return user

def user_required(user: User = Depends(get_current_user)):
    if user.role.name not in ["student", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed!"
        )
    return user
