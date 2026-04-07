from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

# --- Enums ---
class TopicEnum(str, Enum):
    NEIGHBOR_FRIEND = "동네친구"
    RESTAURANT = "맛집"
    GENERAL = "일반"

class ProductStatusEnum(str, Enum):
    FOR_SALE = "판매중"
    SOLD_OUT = "거래완료"

class ReportTargetTypeEnum(str, Enum):
    USER = "USER"
    PRODUCT = "PRODUCT"
    POST = "POST"
    COMMENT = "COMMENT"

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
    neighborhood: Optional[str] = None
class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    avatar: Optional[str] = None

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

class UserAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    avatar: Optional[str] = None
    neighborhood: Optional[str] = None

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

class ProductStatusUpdate(BaseModel):
    status: ProductStatusEnum

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    status: str
    neighborhood: Optional[str] = None
    favorite_count: int = 0
    created_at: datetime
    updated_at: datetime
    user: UserAuthorResponse

class ProductListResponse(BaseModel):
    data: List[ProductResponse]
    next_cursor: Optional[int] = None
    has_more: bool

# --- PostImage Schemas ---
class PostImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str

# --- Comment Schemas ---
class CommentCreate(BaseModel):
    payload: str

class CommentAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    avatar: Optional[str] = None

class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payload: str
    created_at: datetime
    user: CommentAuthorResponse

# --- Post Schemas ---
class PostCreate(BaseModel):
    topic: TopicEnum
    title: str
    description: Optional[str] = None
    image_urls: Optional[List[str]] = None

class PostListItemResponse(BaseModel):
    """게시글 목록 아이템 - 주제, 제목, 내용, 작성자 동네, 시간, 조회수, 댓글 수"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    title: str
    description: Optional[str] = None
    views: int
    created_at: datetime
    comment_count: int
    author: UserAuthorResponse

class PostListResponse(BaseModel):
    data: List[PostListItemResponse]
    next_cursor: Optional[int] = None
    has_more: bool

class PostDetailResponse(BaseModel):
    """게시글 상세 - 주제, 제목, 내용, 작성자 정보, 시간, 조회수, 이미지, 댓글"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    title: str
    description: Optional[str] = None
    views: int
    created_at: datetime
    author: UserAuthorResponse
    images: List[PostImageResponse]
    comments: List[CommentResponse]

# --- Block/Report Schemas ---

class ProductBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    product_id: int
    created_at: datetime

class ReportCreate(BaseModel):
    target_type: ReportTargetTypeEnum
    target_id: int
    reason: str

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str
    status: str
    created_at: datetime
