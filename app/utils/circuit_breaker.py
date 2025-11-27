import pybreaker
import httpx
import asyncio

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1442346731466526804/8ywRfJtn42IRY1HjE3sN5od0JLVD7dKnkJSTa8IXumwNJ8n2wIzZGLi-TwcJ1kKWPK9C"

async def notify_discord(webhook_url: str = DISCORD_WEBHOOK, message: str = "Circuit breaker triggered"):
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={"content": message})

breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    success_threshold=3,
)