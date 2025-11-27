from redis.asyncio import Redis
import os

redis = Redis.from_url(os.getenv("REDIS_URL"), encoding="utf-8", decode_responses=True)