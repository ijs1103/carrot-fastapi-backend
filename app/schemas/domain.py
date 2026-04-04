from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional, List

# --- Generic Tokens ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    github_id: Optional[str] = None
    avatar: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

# --- Product Schemas ---
class ProductBase(BaseModel):
    title: str
    price: float
    photo: str
    description: str

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    photo: Optional[str] = None
    description: Optional[str] = None

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class ProductListResponse(BaseModel):
    data: List[ProductResponse]
    next_cursor: Optional[int] = None
    has_more: bool

# --- Post Schemas ---
class PostBase(BaseModel):
    title: str
    description: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    views: int
    user_id: int
    created_at: datetime
    updated_at: datetime

class PostListResponse(BaseModel):
    data: List[PostResponse]
    next_cursor: Optional[int] = None
    has_more: bool
