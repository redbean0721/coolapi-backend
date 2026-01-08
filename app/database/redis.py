from redis.asyncio import Redis
import os

redis_client: Redis | None = None

async def init_redis():
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

async def close_redis():
    if redis_client:
        await redis_client.close()

async def get_redis() -> Redis:
    if redis_client is None:
        await init_redis()
    return redis_client