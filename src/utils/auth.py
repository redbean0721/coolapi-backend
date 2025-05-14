from fastapi import Response
from src.database.mariadb import query_in_mariadb, get_mariadb_connect
import logging, secrets, time

def verify_api_key(api_key: str) -> bool:
    query = "SELECT COUNT(*) FROM api_keys WHERE api_key = ?"
    values = (api_key,)
    result = query_in_mariadb(query, values)
    return result[0][0] > 0

def permission_check(api_key: str, required_permission: str) -> bool:
    query = "SELECT permissions FROM api_keys WHERE api_key = ?"
    values = (api_key,)
    result = query_in_mariadb(query, values)
    if result:
        permissions = result[0][0]
        if "global" in permissions.split(","):
            return True
        else:
            return required_permission in permissions.split(",")
    else:
        return False

async def setCookie(response: Response, userId: int, loginType: str = "local", cookieName: str = "auth", maxAge: int = 300) -> str:
    conn, cursor = await get_mariadb_connect()
    sessionId = secrets.token_urlsafe(32)
    createdAt = int(time.time())
    expiresAt = createdAt + maxAge

    # 先刪除舊的 session（避免 UNIQUE 衝突）
    cursor.execute("DELETE FROM sessions WHERE user_id = %s", (userId,))

    # 插入新的 session
    cursor.execute(
        """
        INSERT INTO sessions (user_id, payload, login_type, cookie_name, created_at, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (userId, sessionId, loginType, cookieName, createdAt, expiresAt)
    )
    conn.commit()
    cursor.close()

    response.set_cookie(
        key=cookieName,
        value=sessionId,
        max_age=maxAge,
        httponly=True,
        secure=True,
        samesite="Lax"
    )

    return sessionId

async def verifyCookie(sessionId: str) -> bool:
    conn, cursor = await get_mariadb_connect()

    try:
        cursor.execute("SELECT * FROM sessions WHERE payload = %s AND expires_at > %s",(sessionId, int(time.time())))
        result = cursor.fetchone()
        if result: return True
        else: return False
    except Exception as e:
        logging.error(f"Error verifying cookie: {e}")
        return False
    finally:
        cursor.close()
