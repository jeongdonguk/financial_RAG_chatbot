from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.middlewares.access_log import AccessLogMiddleware
from api.routers import pdf_router, stock_router
from core.mongodb import connect_to_mongo, close_mongo_connection
from core.logging import get_logger

log = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 실행
    log.info("애플리케이션 시작")
    try:
        await connect_to_mongo()
    except Exception as e:
        log.warning(f"MongoDB 연결 실패, 계속 진행: {str(e)}")
    yield
    # 종료 시 실행
    log.info("애플리케이션 종료")
    try:
        await close_mongo_connection()
    except Exception as e:
        log.warning(f"MongoDB 연결 종료 실패: {str(e)}")

app = FastAPI(
    title="금융 RAG 챗봇",
    description="금융 데이터 크롤링 및 PDF 관리 API",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(AccessLogMiddleware)

# 라우터 등록
app.include_router(pdf_router.router)
app.include_router(stock_router.router)
