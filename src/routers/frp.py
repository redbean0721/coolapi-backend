from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, EmailStr
from typing import Dict
import logging
import json

router = APIRouter()

class BaseUser(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

class UserIn(BaseUser):
    password: str

class FRP_Login_Request(BaseModel):
    version: str = "0.1.0"
    op: str = "Login"
    content: "Content"

    class Content(BaseModel):
        version: str
        os: str
        arch: str
        user: str   # 必填
        privilege_key: str
        timestamp: int

        class MetaData(BaseModel):
            token: str  # 必填

        metas: MetaData
        client_spec: Dict[str, str]
        pool_count: int
        client_address: str

def load_users():
    with open("users.json", "r") as file:
        return json.load(file)["users"]

users = load_users()

def authenticate_user(user: str, meta_token: str) -> bool:
    for entry in users:
        if entry["user"] == user and entry["meta_token"] == meta_token:
            return True
    return False

@router.post("/frp/login", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def frp_login(request: FRP_Login_Request, op: str = "Login", version: str = "0.1.0"):
    # Check if version and op are provided in the request URL
    if not op or not request.op or not version or not request.version:
        return JSONResponse(content={"reject": True, "reject_reason": "Missing 'op' or 'version' in request"}, status_code=400)
    
    print(request)

    if request.op == "Login" and op == "Login":
        user = request.content.user
        meta_token = request.content.metas.token  # metadatas.token -> metas.token

        if not user or not meta_token:
            return JSONResponse(content={"reject": True, "reject_reason": "Missing authentication information"}, status_code=400)

        # Authenticate user
        if authenticate_user(user, meta_token):
            return JSONResponse(
                content={"reject": False, "unchange": True }, status_code=200)
        else:
            return JSONResponse(content={"reject": True, "reject_reason": "invalid user"}, status_code=401)

    # Handle other operations (currently only Login is implemented)
    return JSONResponse(content={"reject": True, "reject_reason": "unsupported operation"}, status_code=422)
