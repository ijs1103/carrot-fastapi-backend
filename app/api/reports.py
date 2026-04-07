from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import User
from app.schemas.domain import ReportCreate, ReportResponse
from app.crud.domain import create_report, get_existing_report
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReportResponse)
async def create_new_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """게시물, 유저, 댓글 등을 신고합니다."""
    # 중복 신고 방지
    existing_report = await get_existing_report(
        db, 
        reporter_id=current_user.id, 
        target_type=report_data.target_type.value, 
        target_id=report_data.target_id
    )
    
    if existing_report:
        raise HTTPException(status_code=400, detail="이미 신고한 대상입니다.")
        
    report = await create_report(
        db,
        reporter_id=current_user.id,
        target_type=report_data.target_type.value,
        target_id=report_data.target_id,
        reason=report_data.reason
    )
    
    return report
