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

# from starlette.types import ASGIApp, Receive, Scope, Send

# class RequestTimerMiddleware:
#     def __init__(self, app: ASGIApp):
#         self.app = app

#     async def __call__(self, scope: Scope, receive: Receive, send: Send):
#         if scope["type"] != "http":
#             await self.app(scope, receive, send)
#             return

#         start = time.perf_counter()
#         async def send_wrapper(message):
#             if message["type"] == "http.response.start":
#                 elapsed_ms = (time.perf_counter() - start) * 1000
#                 headers = list(message.get("headers", []))
#                 headers.append((b"x-process-time", f"{elapsed_ms:.2f}ms".encode()))
#                 message["headers"] = headers
#             await send(message)

#         await self.app(scope, receive, send_wrapper)