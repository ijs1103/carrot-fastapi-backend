from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.models.domain import User, Product, Post, PostImage, Comment, ProductFavorite, ProductBlock, Report
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

async def get_products(db: AsyncSession, user_id: int = None, status: str = None, cursor: int = None, limit: int = 20, exclude_blocked_by: int = None):
    """상품 목록 조회 (user_id 및 status 필터, 페이지네이션 지원, 차단된 상품 제외)"""
    query = select(Product).options(selectinload(Product.user), selectinload(Product.favorites)).order_by(Product.id.desc()).limit(limit + 1)
    
    if user_id:
        query = query.where(Product.user_id == user_id)
        
    if status:
        query = query.where(Product.status == status)
        
    if exclude_blocked_by:
        query = query.where(Product.id.notin_(
            select(ProductBlock.product_id).where(ProductBlock.user_id == exclude_blocked_by)
        ))
        
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
    # user, favorites 관계를 포함하여 다시 조회
    return await get_product(db, product_id=db_product.id)

async def get_product(db: AsyncSession, product_id: int) -> Product | None:
    result = await db.execute(select(Product).options(selectinload(Product.user), selectinload(Product.favorites)).where(Product.id == product_id))
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

# ==================== Product Favorite CRUD ====================

async def toggle_product_favorite(db: AsyncSession, product_id: int, user_id: int) -> bool:
    """찜하기 토글: 이미 찜한 경우 해제, 아니면 추가. 찜 추가 시 True, 해제 시 False 반환"""
    result = await db.execute(
        select(ProductFavorite).where(
            ProductFavorite.product_id == product_id,
            ProductFavorite.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        await db.delete(existing)
        await db.commit()
        db.expire_all()
        return False
    else:
        fav = ProductFavorite(product_id=product_id, user_id=user_id)
        db.add(fav)
        await db.commit()
        db.expire_all()
        return True

async def is_product_favorited(db: AsyncSession, product_id: int, user_id: int) -> bool:
    """해당 유저가 해당 상품을 찜했는지 여부"""
    result = await db.execute(
        select(ProductFavorite).where(
            ProductFavorite.product_id == product_id,
            ProductFavorite.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None

async def get_user_favorite_products(db: AsyncSession, user_id: int, cursor: int = None, limit: int = 20):
    """유저가 찜한 상품 목록 조회 (페이지네이션 지원)"""
    query = (
        select(Product)
        .join(ProductFavorite, Product.id == ProductFavorite.product_id)
        .where(ProductFavorite.user_id == user_id)
        .options(selectinload(Product.user), selectinload(Product.favorites))
        .order_by(ProductFavorite.created_at.desc())
        .limit(limit + 1)
    )
    
    if cursor:
        query = query.where(Product.id < cursor)
    
    result = await db.execute(query)
    items = list(result.scalars().all())
    
    next_cursor = items[-1].id if len(items) > limit else None
    return items[:limit], next_cursor

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

# ==================== Product Block CRUD ====================

async def block_product(db: AsyncSession, user_id: int, product_id: int) -> ProductBlock:
    """상품 차단"""
    block = ProductBlock(user_id=user_id, product_id=product_id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block

async def unblock_product(db: AsyncSession, user_id: int, product_id: int):
    """상품 차단 해제"""
    await db.execute(
        delete(ProductBlock).where(
            ProductBlock.user_id == user_id,
            ProductBlock.product_id == product_id,
        )
    )
    await db.commit()

async def get_product_block(db: AsyncSession, user_id: int, product_id: int) -> ProductBlock | None:
    """상품 차단 관계 조회"""
    result = await db.execute(
        select(ProductBlock).where(
            ProductBlock.user_id == user_id,
            ProductBlock.product_id == product_id,
        )
    )
    return result.scalar_one_or_none()

# ==================== Report CRUD ====================

async def create_report(db: AsyncSession, reporter_id: int, target_type: str, target_id: int, reason: str) -> Report:
    """신고 생성"""
    report = Report(
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report

async def get_existing_report(db: AsyncSession, reporter_id: int, target_type: str, target_id: int) -> Report | None:
    """중복 신고 확인"""
    result = await db.execute(
        select(Report).where(
            Report.reporter_id == reporter_id,
            Report.target_type == target_type,
            Report.target_id == target_id,
        )
    )
    return result.scalar_one_or_none()
