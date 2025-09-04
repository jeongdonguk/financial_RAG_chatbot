from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from core.config import Settings

# 비동기 엔진 생성 (oracle+asyncpg 사용)
async_database_url = Settings.DATABASE_URL.replace("oracle://", "oracle+asyncpg://")
engine = create_async_engine(async_database_url, pool_pre_ping=True, echo=False)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()