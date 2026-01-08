from app.database.redis import get_redis
import os, secrets

COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_HTTPONLY = bool(os.getenv("COOKIE_HTTPONLY"))
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE"))
COOKIE_PATH = os.getenv("COOKIE_PATH")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")
COOKIE_SECURE = bool(os.getenv("COOKIE_SECURE"))
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")

async def create_session(user_id: int) -> str:
    session_token = secrets.token_urlsafe(32)
    redis = await get_redis()
    await redis.setex(f"session:{session_token}", COOKIE_MAX_AGE, user_id)
    return session_token

async def delete_session(session_token: str) -> None:
    redis = await get_redis()
    await redis.delete(f"session:{session_token}")