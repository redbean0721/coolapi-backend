from fastapi import APIRouter, Depends, Cookie, status, HTTPException
from fastapi.responses import ORJSONResponse
from app.database.redis import redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.mariadb import get_db
from app.database.models import User
from sqlalchemy.future import select
import os

router = APIRouter()
router.router_name = "user"
router.prefix = "/user"

from setuptools._distutils.util import strtobool
COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_HTTPONLY = strtobool(os.getenv("COOKIE_HTTPONLY"))
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE"))
COOKIE_PATH = os.getenv("COOKIE_PATH")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")
COOKIE_SECURE = strtobool(os.getenv("COOKIE_SECURE"))
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")

async def get_current_user(session_token: str = Cookie(None, alias=COOKIE_NAME), db: AsyncSession = Depends(get_db)):
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user_id = await redis.get(f"session:{session_token}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return db_user

@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return ORJSONResponse(content={
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "role": current_user.role,
        # 2fa 分成 totp 和 email, 所以用 list 包起來, e.g. {"totp": true, "email": false}
        "2fa_enabled": {
            "totp": current_user.totp_secret is not None,
            "email": current_user.email_2fa_enabled
        },
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    })

# @router.get("/api-keys")