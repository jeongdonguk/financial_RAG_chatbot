from time import perf_counter
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import get_logger

_access = get_logger("access")

class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = perf_counter()
        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        method = request.method
        path = request.url.path
        query = request.url.query

        status = 500  # 기본값 설정
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            _access.info(
                "access",
                extra={
                    "event": "http_access",
                    "http_method": method,
                    "path": path,
                    "query": query,
                    "status_code": status,
                    "client_ip": client_ip,
                    "duration_ms": duration_ms,
                },
            )
