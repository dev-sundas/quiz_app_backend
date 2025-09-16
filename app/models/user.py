from typing import List, Optional
from sqlalchemy import String
from sqlmodel import Column, ForeignKey, Integer, SQLModel, Field, Relationship
from pydantic import BaseModel
from datetime import datetime, timezone



class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    
class RefreshToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))
    )
    token: str = Field(..., description="The refresh token JWT")
    expires_at: datetime = Field(..., description="When this token expires")
    revoked: bool = Field(default=False, description="If True, token is invalidated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationship back to User (optional)
    user: "User" = Relationship(back_populates="refresh_tokens")


class Token(BaseModel):
    access_token: str
    refresh_token: str     
    token_type: str = "bearer"
    userId: Optional[int] = None   # keep if you still need to send userId in response
    role: Optional[str] = None   # <-- Add role here


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None   # <-- Add role here
   


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str = Field(unique=True, index=True, nullable=False) 
    password_hash: str
    role_id: int = Field(foreign_key="role.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    role: "Role" = Relationship(back_populates="users")
    refresh_tokens: List[RefreshToken] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

# ----------------------------
# Role Table
# ----------------------------
class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None

    users: List["User"] = Relationship(back_populates="role")




