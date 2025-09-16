from typing import Optional
from datetime import datetime
from pydantic import BaseModel


    
# -------- Base Schema --------
class UserBase(BaseModel):
    username: str
    email: str

# -------- Create Schema --------
class UserCreate(UserBase):
    password: str

# -------- Read Schema --------
class UserRead(UserBase):
    id: int
    role:str
    created_at: datetime
    updated_at: datetime


# -------- Update Schema --------
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class AdminUserUpdate(UserUpdate):
    role_id: Optional[int] = None    
# ----------------------------
# Role Schemas
# ----------------------------
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    id: int


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None






