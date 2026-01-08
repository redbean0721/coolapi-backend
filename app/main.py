from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager
from filelock import FileLock
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
import os, time

from app.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在這裡放置啟動代碼
    from app.database.mariadb import init_db
    with FileLock(lock_file="/tmp/db_init.lock"):   # 用於確保只有一個實例執行初始化資料庫
        await init_db()
    
    from app.database.redis import init_redis, close_redis
    await init_redis()
    global start_time
    start_time = int(time.time())
    yield
    await close_redis()
    # 在這裡放置關閉代碼

app = FastAPI(
    title=os.getenv("API_TITLE"),
    version=os.getenv("API_VERSION"),
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

from app.middleware import middlewares
for middleware in middlewares:
    app.add_middleware(middleware)

from app.routers import routers
for router in routers:
    app.include_router(router, prefix="/api", tags=[router.router_name.capitalize()])