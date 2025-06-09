from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from service import count_service
from db.models.finance_data import stock_finance_data
from core.logging import get_logger
from schemas.response import BaseResponse, CountResponse

log = get_logger("finance_data")


router = APIRouter(
    prefix="/finance_data",
)

@router.get("/count", response_model=BaseResponse[CountResponse])
async def get_finance_data_count(db: AsyncSession = Depends(get_db)):
    try:
        count = await count_service.get_count(db, stock_finance_data)
        return BaseResponse(
            success=True,
            message="데이터 조회가 성공적으로 완료되었습니다",
            data=CountResponse(count=count)
        )
    except Exception as e:
        log.error(f"finance_data/count 장애 : {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"데이터 조회 실패: {str(e)}"
        )