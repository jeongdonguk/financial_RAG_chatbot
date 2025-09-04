from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from crawler.core.database import get_db
from crawler.service import count_service
from crawler.db.models.finance_data import stock_finance_data



router = APIRouter(
    prefix="/finance_data",
)

@router.get("/count")
async def get_finance_data_count(db: AsyncSession = Depends(get_db)):
    return await count_service.get_count(db, stock_finance_data)