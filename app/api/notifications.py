from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.domain import User
from app.schemas.domain import FCMTokenUpdate
from sqlalchemy import update

router = APIRouter()

@router.post("/token")
async def update_fcm_token(
    current_user: User = Depends(deps.get_current_user),
    token_in: FCMTokenUpdate = None,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    현재 유저의 FCM 토큰을 업데이트합니다.
    """
    try:
        query = update(User).where(User.id == current_user.id).values(fcm_token=token_in.token)
        await db.execute(query)
        await db.commit()
        return {"status": "ok", "message": "FCM token updated successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update FCM token: {str(e)}"
        )
