from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import os

from app.api import deps
from app.crud import domain as crud
from app.schemas.domain import ChatRoomCreate, ChatRoomInitResponse, InternalMessageCreate, ChatRoomDetailResponse, MessageCreate
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

@router.get("/rooms/me")
async def get_my_rooms(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """현재 유저가 참여 중인 채팅방 목록"""
    room_list = await crud.get_my_chat_rooms(db, user_id=current_user.id)
    
    result = []
    for item in room_list:
        room = item["room"]
        last_msg = item["last_message"]
        
        # 상대방 결정
        other_user = room.seller if room.buyer_id == current_user.id else room.buyer
        
        result.append({
            "id": room.id,
            "product": {
                "id": room.product.id,
                "title": room.product.title,
                "photo": room.product.photo.split(',')[0].strip() if room.product.photo else "",
                "price": room.product.price,
            },
            "other_user": {
                "id": other_user.id,
                "username": other_user.username,
                "avatar": other_user.avatar,
                "neighborhood": other_user.neighborhood,
            },
            "last_message": {
                "payload": last_msg.payload,
                "created_at": last_msg.created_at.isoformat(),
            } if last_msg else None,
            "created_at": room.created_at.isoformat(),
            "updated_at": room.updated_at.isoformat(),
        })
    
    return result

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
    print(f"[WorkerSync] Message saved: room={msg_in.room_id}, user={msg_in.user_id}")
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
        
    # Generate ticket for WebSocket connection
    access_token_expires = timedelta(minutes=60)
    ticket = create_access_token(
        subject=f"{current_user.id}:{room.id}", expires_delta=access_token_expires
    )
    
    # Manually attach ticket to the room object for the response
    room_data = {
        "id": room.id,
        "product_id": room.product_id,
        "buyer_id": room.buyer_id,
        "seller_id": room.seller_id,
        "product": room.product,
        "buyer": room.buyer,
        "seller": room.seller,
        "created_at": room.created_at,
        "updated_at": room.updated_at,
        "ticket": ticket
    }
    return room_data

@router.post("/{room_id}/messages")
async def send_message(
    room_id: str,
    msg_in: MessageCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """WebSocket이 안될 경우를 대비한 일반 메시지 전송 API"""
    room = await crud.get_chat_room(db, room_id=room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
        
    if current_user.id not in [room.buyer_id, room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to send messages to this room")
        
    message = await crud.create_message(
        db,
        room_id=room_id,
        user_id=current_user.id,
        payload=msg_in.payload
    )
    return message

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

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def leave_chat_room(
    room_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """채팅방 나가기 (소프트 나가기 — 둘 다 나가면 실제 삭제)"""
    room = await crud.get_chat_room(db, room_id=room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in [room.buyer_id, room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to leave this room")
    
    await crud.leave_chat_room(db, room_id=room_id, user_id=current_user.id)

