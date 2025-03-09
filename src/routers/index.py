from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
import time

router = APIRouter()

@router.get("/", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def index():
    return JSONResponse(content={"status": "OK"})


@router.get("/status", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def status():
    from src.main import start_time
    # now_time = int(time.time())
    return JSONResponse(content={"start_time": f"{start_time}"})
