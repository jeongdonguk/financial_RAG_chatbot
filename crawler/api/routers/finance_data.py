from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from service import count_service
from db.models.finance_data import stock_finance_data
from core.logging import get_logger

log = get_logger("finance_data")


router = APIRouter(
    prefix="/finance_data",
)

@router.get("/count")
async def get_finance_data_count(db: AsyncSession = Depends(get_db)):
    try:
        return await count_service.get_count(db, stock_finance_data)
    except Exception as e:
        log.error(f"finance_data/count 장애 : {str(e)}")
        return {"error": f"Database connection failed: {str(e)}", "count": 0}