from __future__ import annotations
from typing import Optional
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.requests import Request
from app.database.modules import Event, UserEventLog, User

# RQ/Redis are sync; enqueue is very fast and OK inside async endpoints
from rq import Queue
from redis import Redis  # Sync Redis for RQ

REDIS_URL = os.getenv("REDIS_URL")
EMAIL_QUEUE_NAME = os.getenv("EMAIL_QUEUE_NAME", "email")
EMAIL_JOB_PATH = os.getenv("SECURITY_EMAIL_JOB", "app.tasks.send_security_email")


def _get_client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    # Prioritize X-Forwarded-For when behind proxy
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # take first IP in list
        return xff.split(",")[0].strip()
    client = request.client
    return client.host if client else None


def _get_user_agent(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    return request.headers.get("user-agent")


async def ensure_event(db: AsyncSession, key: str, description: Optional[str] = None) -> Event:
    stmt = select(Event).where(Event.key == key)
    res = await db.execute(stmt)
    evt: Optional[Event] = res.scalar_one_or_none()
    if evt:
        return evt
    evt = Event(key=key, description=description)
    db.add(evt)
    await db.commit()
    await db.refresh(evt)
    return evt


async def log_and_notify(
    db: AsyncSession,
    *,
    event_key: str,
    user: Optional[User] = None,
    request: Optional[Request] = None,
    message: Optional[str] = None,
    send_email: bool = False,
    email: Optional[str] = None,
    email_payload: Optional[dict] = None,
) -> None:
    """
    Unified audit helper: write user event log and optionally enqueue email job.
    - Creates Event record on first use (by key)
    - Inserts a UserEventLog row
    - Enqueues an email job to RQ if requested
    """
    evt = await ensure_event(db, event_key)

    log = UserEventLog(
        user_id=user.id if user else None,
        event_id=evt.id,
        ip_address=_get_client_ip(request),
        user_agent=_get_user_agent(request),
        message=message,
    )
    db.add(log)
    await db.commit()

    if send_email and email:
        try:
            conn = Redis.from_url(REDIS_URL, decode_responses=True)
            q = Queue(EMAIL_QUEUE_NAME, connection=conn)
            payload = email_payload or {}
            # Flexible generic security email task
            q.enqueue(EMAIL_JOB_PATH, email, event_key, payload, job_timeout=300)
        except Exception as e:
            # Avoid breaking main flow if queue is down
            print(f"[audit] enqueue email failed: {e}")
