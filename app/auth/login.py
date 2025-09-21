# from typing import Annotated
import json
from typing import Annotated
from fastapi import APIRouter, Body, Cookie, Depends, Form, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import selectinload
from app.db import get_session
from app.models.user import LogoutRequest, User, RefreshToken, Token, TokenData
from app.auth.utils import verify_password
from app.auth.deps import ALGORITHM, SECRET_KEY, authenticate_user, create_access_token, create_refresh_token, get_current_user

# ---------------------
# Constants
# ---------------------
SLIDING_EXPIRATION_HOURS = 2
ACCESS_TOKEN_EXPIRE_MINUTES = 15

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------------------
# Helper: UTC now
# ---------------------

def now_utc_naive() -> datetime:
    return datetime.utcnow()  # naive UTC



# ---------------------
# Validate & slide refresh token
# ---------------------
async def is_valid_refresh_token(session: AsyncSession, username: str, token: str) -> bool:
    result = await session.exec(
        select(RefreshToken).join(User).where(User.username == username, RefreshToken.token == token)
    )
    db_token = result.first()
    if not db_token:
        return False

    # Compare UTC
    if db_token.expires_at < now_utc_naive():
        return False

    # Sliding expiration: extend token expiry
    db_token.expires_at = now_utc_naive() + timedelta(hours=SLIDING_EXPIRATION_HOURS)
    session.add(db_token)
    await session.commit()
    return True

# ---------------------
# Save refresh token
# ---------------------
async def save_refresh_token(session: AsyncSession, user_id: int, token: str):
    expires_at = now_utc_naive() + timedelta(hours=SLIDING_EXPIRATION_HOURS)
    db_token = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    session.add(db_token)
    await session.commit()

# ---------------------
# Login & issue tokens (updated)
# ---------------------
@auth_router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)]
):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.name},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 🔹 CHANGED: Revoke all old refresh tokens on login
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(revoked=True)
    )
    await session.commit()

    # 🔹 CHANGED: Always create a new refresh token
    refresh_token = create_refresh_token(data={"sub": user.username})
    await save_refresh_token(session, user.id, refresh_token)

    # return JSON with tokens
    response = JSONResponse(content={
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "userId": user.id,
        "role": user.role.name
    })

    # Set HttpOnly cookies (refresh and access) 🔹 CHANGED
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=True,
        samesite="none"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=SLIDING_EXPIRATION_HOURS * 3600,
        secure=True,
        samesite="none"
    )

    return response


# ---------------------
# Refresh endpoint (updated)
# ---------------------
@auth_router.post("/refresh")
async def refresh_token_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: str = Cookie(None)  # read refresh token from cookie
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # 🔹 CHANGED: Validate old token
        valid = await is_valid_refresh_token(session, username, refresh_token)
        if not valid:
            raise HTTPException(status_code=401, detail="Expired or revoked refresh token")

        result = await session.exec(select(User).where(User.username == username).options(selectinload(User.role)))
        user = result.first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create new access token
        access_token = create_access_token(
            data={"sub": username, "role": user.role.name},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # 🔹 CHANGED: Rotate refresh token
        new_refresh_token = create_refresh_token(data={"sub": username})
        # Revoke old token
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token == refresh_token)
            .values(revoked=True)
        )
        await session.commit()
        # Save new token
        await save_refresh_token(session, user.id, new_refresh_token)

        # 🔹 CHANGED: Return and set new cookies
        response = JSONResponse(content={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        })

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,
            samesite="none"
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=SLIDING_EXPIRATION_HOURS * 3600,
            secure=True,
            samesite="none"
        )

        return response

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")



@auth_router.post("/logout")
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    request: LogoutRequest | None = None,
    user: Annotated[User | None, Depends(get_current_user)] = None,
):
    if user:
        # Revoke all refresh tokens for this user
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(revoked=True)
        )
        await session.commit()

        response.delete_cookie(
        key="access_token",
        secure=True,
        samesite="none"
        )
        response.delete_cookie(
            key="refresh_token",
            secure=True,
            samesite="none"
        )
        return {"msg": "Logged out with access token"}

    elif request and request.refresh_token:
        result = await session.exec(
            select(RefreshToken).where(RefreshToken.token == request.refresh_token)
        )
        db_token = result.first()
        if db_token:
            db_token.revoked = True
            session.add(db_token)
            await session.commit()

        response.delete_cookie(
        key="access_token",
        path="/",
        secure=True,
        samesite="none"
        )
        response.delete_cookie(
            key="refresh_token",
            path="/",
            secure=True,
            samesite="none"
        )
        return {"msg": "Logged out with refresh token"}

    raise HTTPException(status_code=401, detail="No valid token for logout")
