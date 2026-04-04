from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.domain import User, Product
from app.schemas.domain import UserCreate, ProductCreate
from app.core.security import get_password_hash

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        phone=user_in.phone,
        password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_products(db: AsyncSession, cursor: int = None, limit: int = 20):
    query = select(Product).order_by(Product.id.desc()).limit(limit + 1)
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
