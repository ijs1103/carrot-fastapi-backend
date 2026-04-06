from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import User
from app.schemas.domain import ProductCreate, ProductResponse, ProductListResponse, ProductStatusUpdate, ProductStatusEnum
from app.crud.domain import get_products, create_product, get_product, delete_product, update_product_status, toggle_product_favorite, is_product_favorited, get_user_favorite_products
from app.api.deps import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=ProductListResponse)
async def read_products(
    cursor: int = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    items, next_cursor = await get_products(db, cursor=cursor, limit=limit, status=ProductStatusEnum.FOR_SALE.value)
    return ProductListResponse(
        data=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None
    )

@router.get("/me", response_model=ProductListResponse)
async def read_user_products(
    status: str = Query(None, description="Filter by status (판매중 or 거래완료)"),
    cursor: int = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인한 사용자가 등록한 상품 목록 조회 (페이지네이션 지원)"""
    items, next_cursor = await get_products(db, user_id=current_user.id, status=status, cursor=cursor, limit=limit)
    return ProductListResponse(
        data=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None
    )

@router.get("/me/favorites", response_model=ProductListResponse)
async def read_my_favorites(
    cursor: int = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내가 찜한 상품 목록 조회 (페이지네이션 지원)"""
    items, next_cursor = await get_user_favorite_products(db, user_id=current_user.id, cursor=cursor, limit=limit)
    return ProductListResponse(
        data=items,
        next_cursor=next_cursor,
        has_more=next_cursor is not None
    )

@router.get("/{id}", response_model=ProductResponse)
async def read_product(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    product = await get_product(db, product_id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_new_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_product(db, product_in=product_in, user_id=current_user.id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    product = await get_product(db, product_id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")
    
    await delete_product(db, product_id=id)
    return None

@router.patch("/{id}/status", response_model=ProductResponse)
async def update_status(
    id: int,
    status_update: ProductStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """상품 상태 변경 (본인만 가능)"""
    product = await get_product(db, product_id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")
        
    updated_product = await update_product_status(db, product=product, status=status_update.status.value)
    return updated_product


# ==================== 찜하기 API ====================

@router.post("/{id}/favorite")
async def toggle_favorite(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """상품 찜하기 토글 (찜 추가/해제)"""
    product = await get_product(db, product_id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    is_favorited = await toggle_product_favorite(db, product_id=id, user_id=current_user.id)
    # 변경 후 최신 상품 정보 다시 조회
    updated_product = await get_product(db, product_id=id)
    return {
        "is_favorited": is_favorited,
        "favorite_count": updated_product.favorite_count,
    }

@router.get("/{id}/favorite")
async def check_favorite(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """해당 상품에 대한 찜 여부 확인"""
    product = await get_product(db, product_id=id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    favorited = await is_product_favorited(db, product_id=id, user_id=current_user.id)
    return {
        "is_favorited": favorited,
        "favorite_count": product.favorite_count,
    }
