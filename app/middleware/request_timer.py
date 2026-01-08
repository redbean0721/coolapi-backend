from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class RequestTimerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)     # 執行請求處理鏈
        process_time = (time.perf_counter() - start_time) * 1000  # 轉換為毫秒
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"  # 2 位小數 + ms
        return response