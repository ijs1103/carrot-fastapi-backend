from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import os

from app.api import deps
from app.crud import domain as crud
from app.schemas.domain import ChatRoomCreate, ChatRoomInitResponse, InternalMessageCreate, ChatRoomDetailResponse
from app.models.domain import User
from app.core.security import create_access_token

router = APIRouter()

CF_WORKER_SECRET = os.getenv("CF_WORKER_SECRET", "super-secret-internal-key")

@router.post("/rooms", response_model=ChatRoomInitResponse)
async def get_or_create_room(
    room_in: ChatRoomCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    product = await crud.get_product(db, product_id=room_in.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    # If Seller is clicking, find the first available room for this product
    if product.user_id == current_user.id:
        room = await crud.get_seller_chat_room(db, product_id=product.id, seller_id=current_user.id)
        if not room:
             raise HTTPException(status_code=400, detail="아직 대화 중인 채팅방이 없습니다.")
    else:
        # Buyer is clicking, get or create
        room, is_new = await crud.get_or_create_chat_room(
            db, 
            product_id=product.id,
            buyer_id=current_user.id,
            seller_id=product.user_id
        )
    
    access_token_expires = timedelta(minutes=60) # Increased for stability
    ticket_payload = {
        "sub": f"{current_user.id}:{room.id}"
    }
    ticket = create_access_token(
        subject=ticket_payload["sub"], expires_delta=access_token_expires
    )
    
    return {"room": room, "ticket": ticket}

@router.post("/internal/messages", status_code=status.HTTP_201_CREATED)
async def save_message_internal(
    msg_in: InternalMessageCreate,
    x_internal_secret: str = Header(...),
    db: AsyncSession = Depends(deps.get_db)
):
    if x_internal_secret != CF_WORKER_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized request from worker")
        
    message = await crud.create_message(
        db,
        room_id=msg_in.room_id,
        user_id=msg_in.user_id,
        payload=msg_in.payload
    )
    return {"status": "ok", "message_id": message.id}

@router.get("/{room_id}", response_model=ChatRoomDetailResponse)
async def get_room_detail(
    room_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    room = await crud.get_chat_room(db, room_id=room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
        
    if current_user.id not in [room.buyer_id, room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view this room")
        
    return room

@router.get("/{room_id}/messages")
async def get_messages_for_room(
    room_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    # Verify user is part of this room
    room = await crud.get_chat_room(db, room_id=room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in [room.buyer_id, room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view messages in this room")
        
    messages = await crud.get_chat_messages(db, room_id=room_id)
    
    # Map to schema expected by frontend
    return [
        {
            "id": m.id,
            "payload": m.payload,
            "created_at": m.created_at,
            "userId": m.user_id,
            "chatRoomId": m.chat_room_id,
            "user": {
                "username": m.user.username,
                "avatar": m.user.avatar
            }
        }
        for m in messages
    ]
