from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from core.config import Settings
from core.logging import get_logger
from typing import Optional

log = get_logger("mongodb")
settings = Settings()

# 전역 인스턴스
client: Optional[AsyncIOMotorClient] = None
database: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """MongoDB 연결"""
    global client, database

    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = client[settings.MONGODB_DATABASE]

        # 연결 테스트
        await client.admin.command('ping')
        log.info(f"MongoDB 연결 성공: {settings.MONGODB_DATABASE}")

    except Exception as e:
        log.error(f"MongoDB 연결 실패: {str(e)}")
        raise


async def close_mongo_connection():
    """MongoDB 연결 종료"""
    global client
    if client:
        client.close()
        log.info("MongoDB 연결 종료")

def get_database() -> AsyncIOMotorDatabase:
    """MongoDB 데이터베이스 인스턴스 반환"""
    if database is None:
        raise ValueError("MongoDB 데이터베이스가 연결되지 않았습니다.")
    return database

def get_collection(collection_name: Optional[str] = None):
    """MongoDB 컬렉션 인스턴스 반환"""
    if database is None:
        raise ValueError("MongoDB 데이터베이스가 연결되지 않았습니다.")
    if collection_name is None:
        if settings.MONGODB_COLLECTION is None:
            raise ValueError("MONGODB_COLLECTION 설정이 없습니다.")
        collection_name = settings.MONGODB_COLLECTION
    return database[collection_name]
