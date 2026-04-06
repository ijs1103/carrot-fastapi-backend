from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import User
from app.schemas.domain import (
    PostCreate, PostListResponse, PostListItemResponse, PostDetailResponse,
    UserAuthorResponse, PostImageResponse,
    CommentCreate, CommentResponse,
)
from app.crud.domain import (
    get_posts, get_post, create_post, delete_post, increment_post_views,
    create_comment, get_comment, delete_comment,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/posts", tags=["posts"])


# ==================== 게시글 API ====================

@router.get("", response_model=PostListResponse)
async def read_posts(
    cursor: int = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """게시글 목록 조회"""
    items, next_cursor = await get_posts(db, cursor=cursor, limit=limit)
    return PostListResponse(
        data=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None,
    )


@router.get("/{id}", response_model=PostDetailResponse)
async def read_post(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """게시글 상세 조회 (조회수 자동 +1)"""
    post = await get_post(db, post_id=id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 조회수 증가
    await increment_post_views(db, post)
    
    return PostDetailResponse(
        id=post.id,
        topic=post.topic,
        title=post.title,
        description=post.description,
        views=post.views,
        created_at=post.created_at,
        author=UserAuthorResponse(
            id=post.user.id,
            username=post.user.username,
            avatar=post.user.avatar,
            neighborhood=post.user.neighborhood,
        ),
        images=[PostImageResponse(id=img.id, url=img.url) for img in post.images],
        comments=[
            CommentResponse(
                id=c.id,
                payload=c.payload,
                created_at=c.created_at,
                user={
                    "id": c.user.id,
                    "username": c.user.username,
                    "avatar": c.user.avatar,
                },
            )
            for c in post.comments
        ],
    )


@router.post("", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_new_post(
    post_in: PostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """게시글 생성"""
    new_post = await create_post(db, post_in=post_in, user_id=current_user.id)
    # 생성된 게시글을 상세 조회 형태로 반환
    post = await get_post(db, post_id=new_post.id)
    return PostDetailResponse(
        id=post.id,
        topic=post.topic,
        title=post.title,
        description=post.description,
        views=post.views,
        created_at=post.created_at,
        author=UserAuthorResponse(
            id=post.user.id,
            username=post.user.username,
            avatar=post.user.avatar,
            neighborhood=post.user.neighborhood,
        ),
        images=[PostImageResponse(id=img.id, url=img.url) for img in post.images],
        comments=[],
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_post(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """게시글 삭제 (본인만 가능)"""
    post = await get_post(db, post_id=id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    await delete_post(db, post_id=id)


# ==================== 댓글 API ====================

@router.post("/{id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """게시글에 댓글 작성"""
    post = await get_post(db, post_id=id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    new_comment = await create_comment(db, post_id=id, payload=comment_in.payload, user_id=current_user.id)
    comment = await get_comment(db, comment_id=new_comment.id)
    return comment


@router.delete("/{id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment(
    id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """댓글 삭제 (본인만 가능)"""
    comment = await get_comment(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    await delete_comment(db, comment_id=comment_id)
