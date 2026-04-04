from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Create async engine for MySQL
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Session factory for DB operations
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# FastAPI Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
