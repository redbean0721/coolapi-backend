from slowapi import Limiter
import os

limiter = Limiter(
    key_func=lambda request: request.client.host,
    default_limits=["10/second", "300/minute", "7200/hour", "28800/day"],
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    headers_enabled=True,
)