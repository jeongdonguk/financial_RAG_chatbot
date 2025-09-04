# 기본 셀렉트 관련 쿼리 사용을 위한 파일
from typing import Any, List, Optional, Dict
from crawler.core.database import Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, not_, func, select

async def get_count(db: AsyncSession, model: Base) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar()