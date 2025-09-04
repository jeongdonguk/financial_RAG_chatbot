from fastapi import FastAPI
from api.middlewares.access_log import AccessLogMiddleware
from api.routers import finance_data

app = FastAPI(
    title="금융 RAG 챗봇",
    description="API",
    version="1.0.0"
)
app.add_middleware(AccessLogMiddleware)

# 라우터 등록
app.include_router(finance_data.router)
