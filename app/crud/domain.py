from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.models.domain import User, Product, Post, PostImage, Comment
from app.schemas.domain import UserCreate, ProductCreate, PostCreate, CommentCreate, UserUpdate
from app.core.security import get_password_hash

# ==================== User CRUD ====================

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        phone=user_in.phone,
        neighborhood=user_in.neighborhood,
        password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user: User, user_in: UserUpdate) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# ==================== Product CRUD ====================

async def get_products(db: AsyncSession, user_id: int = None, status: str = None, cursor: int = None, limit: int = 20):
    """상품 목록 조회 (user_id 및 status 필터, 페이지네이션 지원)"""
    query = select(Product).options(selectinload(Product.user)).order_by(Product.id.desc()).limit(limit + 1)
    
    if user_id:
        query = query.where(Product.user_id == user_id)
        
    if status:
        query = query.where(Product.status == status)
        
    if cursor:
        query = query.where(Product.id < cursor)
        
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    next_cursor = items[-1].id if len(items) > limit else None
    return items[:limit], next_cursor

async def create_product(db: AsyncSession, product_in: ProductCreate, user_id: int) -> Product:
    db_product = Product(**product_in.model_dump(), user_id=user_id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def get_product(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(select(Product).options(selectinload(Product.user)).where(Product.id == product_id))
    return result.scalar_one_or_none()

async def update_product_status(db: AsyncSession, product: Product, status: str) -> Product:
    product.status = status
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

async def delete_product(db: AsyncSession, product_id: int):
    await db.execute(delete(Product).where(Product.id == product_id))
    await db.commit()

# ==================== Post CRUD ====================

async def get_posts(db: AsyncSession, cursor: int = None, limit: int = 20):
    """게시글 목록 조회 (댓글 수 포함, 커서 기반 페이지네이션)"""
    # 서브쿼리로 댓글 수 계산
    comment_count_subq = (
        select(Comment.post_id, func.count(Comment.id).label("comment_count"))
        .group_by(Comment.post_id)
        .subquery()
    )
    
    query = (
        select(Post, func.coalesce(comment_count_subq.c.comment_count, 0).label("comment_count"))
        .outerjoin(comment_count_subq, Post.id == comment_count_subq.c.post_id)
        .options(selectinload(Post.user))
        .order_by(Post.id.desc())
        .limit(limit + 1)
    )
    
    if cursor:
        query = query.where(Post.id < cursor)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for row in rows[:limit]:
        post = row[0]
        count = row[1]
        items.append({
            "id": post.id,
            "topic": post.topic,
            "title": post.title,
            "description": post.description,
            "views": post.views,
            "created_at": post.created_at,
            "comment_count": count,
            "author": {
                "id": post.user.id,
                "username": post.user.username,
                "avatar": post.user.avatar,
                "neighborhood": post.user.neighborhood,
            }
        })
    
    next_cursor = rows[limit][0].id if len(rows) > limit else None
    return items, next_cursor

async def get_post(db: AsyncSession, post_id: int) -> Post | None:
    """게시글 상세 조회 (작성자, 이미지, 댓글+댓글 작성자 eager loading)"""
    query = (
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.user),
            selectinload(Post.images),
            selectinload(Post.comments).selectinload(Comment.user),
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def increment_post_views(db: AsyncSession, post: Post):
    """조회수 +1"""
    post.views = post.views + 1
    await db.commit()
    await db.refresh(post)

async def create_post(db: AsyncSession, post_in: PostCreate, user_id: int) -> Post:
    """게시글 생성 (이미지 포함)"""
    db_post = Post(
        topic=post_in.topic.value,
        title=post_in.title,
        description=post_in.description,
        user_id=user_id,
    )
    db.add(db_post)
    await db.flush()  # post.id 확보
    
    # 이미지가 있으면 함께 저장
    if post_in.image_urls:
        for url in post_in.image_urls:
            db_image = PostImage(url=url, post_id=db_post.id)
            db.add(db_image)
    
    await db.commit()
    await db.refresh(db_post)
    return db_post

async def delete_post(db: AsyncSession, post_id: int):
    """게시글 삭제"""
    await db.execute(delete(Post).where(Post.id == post_id))
    await db.commit()

# ==================== Comment CRUD ====================

async def create_comment(db: AsyncSession, post_id: int, payload: str, user_id: int) -> Comment:
    """댓글 생성"""
    db_comment = Comment(
        payload=payload,
        post_id=post_id,
        user_id=user_id,
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def get_comment(db: AsyncSession, comment_id: int) -> Comment | None:
    """댓글 조회"""
    query = (
        select(Comment)
        .where(Comment.id == comment_id)
        .options(selectinload(Comment.user))
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def delete_comment(db: AsyncSession, comment_id: int):
    """댓글 삭제"""
    await db.execute(delete(Comment).where(Comment.id == comment_id))
    await db.commit()

