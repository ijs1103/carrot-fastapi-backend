from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import User
from app.schemas.domain import ProductCreate, ProductResponse, ProductListResponse
from app.crud.domain import get_products, create_product
from app.api.deps import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=ProductListResponse)
async def read_products(
    cursor: int = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    items, next_cursor = await get_products(db, cursor=cursor, limit=limit)
    return ProductListResponse(
        data=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None
    )

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_new_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_product(db, product_in=product_in, user_id=current_user.id)
