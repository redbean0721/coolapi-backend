from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter()
router.router_name = "index"
router.prefix = ""

@router.get("/")
async def index():
    return ORJSONResponse(content={"message": "Welcome to the API"})

@router.get("/status")
async def status():
    return ORJSONResponse(content={"status": "OK"})