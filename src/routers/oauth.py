from fastapi import Depends, APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, HttpUrl, EmailStr
from src.database.mariadb import get_mariadb_connect
from src.utils.auth import setCookie, verifyCookie
from urllib.parse import urlencode
from typing import Union
import httpx, os, time

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@router.get("/oauth/google/login", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def oauth_login_google():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(google_auth_url)

class GoogleUserInfo(BaseModel):
    email: str
    name: str
    google_id: str
    picture: HttpUrl

class ErrorResponse(BaseModel):
    error: str

@router.get("/oauth/google/callback", dependencies=[Depends(RateLimiter(times=120, seconds=60))], response_model=Union[GoogleUserInfo, ErrorResponse])
async def oauth_login_google(request: Request):
    error = request.query_params.get("error")
    if error:
        return {"error": "Google login denied"}

    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing code from Google"}

    # 1. 用 code 換 token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=data)
        token_json = token_resp.json()

    access_token = token_json.get("access_token")

    if not access_token:
        return {"error": "Failed to get token"}

    # 2. 用 token 拿使用者資料
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_resp.json()

    return JSONResponse(content={"email": user_data.get("email"), "name": user_data.get("name"), "google_id": user_data.get("id"), "picture": user_data.get("picture")}, status_code=200)



DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

@router.get("/oauth/discord/login", dependencies=[Depends(RateLimiter(times=120, seconds=60))])
async def oauth_login_discord():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify email"
    }
    url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url)

class DiscordUserInfo(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: str | None
    email: EmailStr | None
    sessionId: str

@router.get("/oauth/discord/callback", dependencies=[Depends(RateLimiter(times=120, seconds=60))], response_model=DiscordUserInfo)
async def discord_callback(request: Request, response: Response):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(content={"error": "Missing code from Discord"}, status_code=400)

    # 取得 access token
    token_data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify email",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://discord.com/api/oauth2/token", data=token_data, headers=headers)
        token_json = token_resp.json()

    access_token = token_json.get("access_token")
    if not access_token:
        return JSONResponse(content={"error": "Failed to get token"}, status_code=400)

    # 取得 Discord 使用者資料
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_resp.json()

    discord_user_id = int(user_data.get("id"))
    discord_username = user_data.get("username")
    email = user_data.get("email")
    avatar_hash = user_data.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_user_id}/{avatar_hash}.png"
    discriminator = user_data.get("discriminator")

    conn, cursor = await get_mariadb_connect()
    status_code = 200
    message = "登入成功"

    # 是否已綁定 Discord
    cursor.execute("SELECT user_id FROM user_oauth_accounts WHERE provider = %s AND user_id = %s", ("discord", discord_user_id))
    row = cursor.fetchone()

    if row:
        user_id = row["user_id"]
    else:
        # 檢查 email 是否已存在於本地帳號
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone()

        if user_row:
            # email 存在，自動連結
            user_id = user_row["id"]
            message = "已連結本地帳號"
            status_code = 201
        else:
            # 完全新註冊
            cursor.execute(
                """
                INSERT INTO users (username, email, name_first, name_last, avatar)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (discord_username, email, discord_username, discord_username, avatar_url)
            )
            conn.commit()
            user_id = cursor.lastrowid
            message = "註冊成功"
            status_code = 201

        # 綁定 Discord 資訊
        cursor.execute(
            """
            INSERT INTO user_oauth_accounts (user_id, provider, external_id, email)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, "discord", discord_user_id, email)
        )
        conn.commit()

    # 設定 session cookie
    sessionId = await setCookie(response=response, userId=user_id, loginType="discord", cookieName="auth", maxAge=300)

    cursor.close()
    return JSONResponse(
        status_code=status_code,
        content={
            "id": discord_user_id,
            "username": discord_username,
            "discriminator": discriminator,
            "avatar": avatar_url,
            "email": email,
            "sessionId": sessionId,
            "message": message
        }
    )

    




    
    # user_id = f"discord_{user_data.get('id')}"

    # 建立 session 並設置 cookie
    # sessionId = await setCookie(userId=userId, loginType="discord", cookieName="auth", maxAge=180)
    # response = RedirectResponse(url="/api/check_cookie")
    # await setcookie(response, session_id)
    # return response

    # return {
    #     "id": user_data.get("id"),
    #     "username": user_data.get("username"),
    #     "discriminator": user_data.get("discriminator"),
    #     "avatar": user_data.get("avatar"),
    #     "email": user_data.get("email"),
    # }

# email
# id google_id
# username name
# avatar picture
# discriminator