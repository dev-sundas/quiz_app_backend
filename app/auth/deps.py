from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio.session import AsyncSession
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import Depends,HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from jose import JWTError,jwt
from app.auth.utils import verify_password
from app.models.user import TokenData,User
from app.db import get_session
from fastapi import Depends, HTTPException
import os
SECRET_KEY = os.getenv("SECRET_KEY","fallback_secret")

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def authenticate_user(session:AsyncSession, username: str, password: str):
    result = await session.exec(select(User).where(User.username == username).options(selectinload(User.role))  # eager load the role
)
    user = result.first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=15)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)




async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str, Depends(oauth2_scheme)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        print("Decoded payload:", payload)
        if username is None or role is None:
            raise credentials_exception

        token_data = TokenData(username=username, role=role)

    except JWTError:
        raise credentials_exception

    result = await session.exec(
        select(User)
        .where(User.username == token_data.username)
        .options(selectinload(User.role))   # eager load role here too
    )
    user = result.one_or_none()
   # print("Fetched user:", user)
    # print("Fetched role:", user.role.name if user and user.role else None)
    # print("Issuing access token for:", user.username, "role:", user.role.name)

    if user is None:
        raise credentials_exception

    return user  # return the actual User model (with role info)

     
    


    
        
    
    