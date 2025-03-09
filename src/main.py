import logging, os, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from src.database.mariadb import check_mariadb_connect
from src.database.mongodb import check_mongodb_connect
from src.utils.counter import check_counter


@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url(url=os.getenv("REDIS_URL"), encoding="utf8")
    await FastAPILimiter.init(redis_connection)
    await check_mariadb_connect()
    await check_mongodb_connect()
    check_counter()
    logging.info("Done!")
    global start_time
    start_time = int(time.time())
    yield
    await FastAPILimiter.close()

app = FastAPI(title=os.getenv("API_TITLE"), version=os.getenv("API_VERSION"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 這裡可以指定具體的來源，例如 ["http://127.0.0.1:9002"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

routers_directory = os.path.join(os.path.dirname(__file__), "routers")
router_names = [
    filename[:-3]  # 去掉 ".py" 後綴
    for filename in os.listdir(routers_directory)
    if filename.endswith(".py") and filename != "__init__.py"
]

# 將 "index" 模塊移到列表的開頭
if "index" in router_names:
    router_names.remove("index")
    router_names.insert(0, "index")

# 動態導入並註冊路由
for router_name in router_names:
    module = __import__(f"src.routers.{router_name}", fromlist=["router"])
    router = getattr(module, "router")
    app.include_router(router=router, tags=[router_name], deprecated=False)
    logging.info(f"Loaded Routing module: {router_name}")
