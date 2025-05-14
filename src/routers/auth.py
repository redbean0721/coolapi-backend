from fastapi import Depends, APIRouter, Security, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, EmailStr
from src.database.mariadb import get_mariadb_connect
from src.utils.auth import setCookie, verifyCookie
import datetime
import bcrypt
import logging
import jwt
import os

# JWT Secret Key (請換成更安全的密鑰)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRATION_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRATION_MINUTES"))  # Token 有效時間（分鐘）

router = APIRouter()

class LoginRequest(BaseModel):
    username: str = None  # 如果未提供，則為 None
    email: EmailStr = None  # 如果未提供，則為 None
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    name_first: str = None  # 如果未提供，則為 None
    name_last: str = None   # 如果未提供，則為 None

@router.post("/auth/login", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def auth_login(request: LoginRequest, response: Response):
    conn, cursor = await get_mariadb_connect()

    if not request.username and not request.email:
        raise HTTPException(status_code=400, detail="Username or email is required")
    if request.username and "@" in request.username:
        raise HTTPException(status_code=400, detail="Invalid username")

    try:
        # 查詢使用者資料
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (request.username, request.email))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid username or email")

        userId = user["id"]
        username = user["username"]
        email = user["email"]
        hashed_password = user["password"]

        # 如果密碼為空，代表可能是第三方登入帳號
        if not hashed_password:
            # 查詢綁定的 OAuth provider
            cursor.execute("SELECT provider FROM user_oauth_accounts WHERE user_id = %s", (userId,))
            oauth = cursor.fetchone()

            if oauth:
                provider = oauth["provider"]
                redirect_url = f"/api/oauth/{provider}/login"
                return JSONResponse(status_code=307, content={
                    "message": f"請透過 {provider.capitalize()} 登入",
                    "provider": provider,
                    "redirect": redirect_url
                })
            else:
                raise HTTPException(status_code=401, detail="此帳號尚未設定密碼或綁定第三方登入")

        # 驗證密碼
        if not bcrypt.checkpw(request.password.encode("utf-8"), hashed_password.encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid password")

        # 登入成功，設置 Cookie
        sessionId = await setCookie(response=response, userId=userId, loginType="local", cookieName="auth", maxAge=300)
        return JSONResponse(content={
            "message": "Login successful",
            "sessionId": sessionId,
            "userId": userId,
            "username": username,
            "email": email
        }, status_code=200)
    
    except HTTPException:
        # 如果是 HTTPException，則直接拋出
        raise
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()


@router.post("/auth/register", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def auth_register(request: RegisterRequest):
    # Check if the username or email is already taken
    # If not, hash the password and insert the user into the database
    # 檢查 username 或 email 是否已被註冊
    conn, cursor = await get_mariadb_connect()
    if request.username and "@" in request.username:
        raise HTTPException(status_code=400, detail="Invalid username")
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (request.username, request.email))
        existing_user = cursor.fetchall()
        if existing_user:
            raise HTTPException(status_code=409, detail="Username or email already exists")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # Hash the password
    # 加密密碼
    hashed_password = bcrypt.hashpw(request.password.encode("utf-8"), bcrypt.gensalt()).decode()

    # Set default values for name_first and name_last if not provided
    name_first = request.name_first or request.username
    name_last = request.name_last or request.username

    # Insert the user into the database
    # 將用戶存入資料庫
    if not request.name_first:
        request.name_first = request.username  # 如果沒有提供 name_first，則使用 username
    if not request.name_last:
        request.name_last = request.username  # 如果沒有提供 name_last，則使用 username
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, name_first, name_last, password)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (request.username, request.email, name_first, name_last, hashed_password)
        )
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Database error (insert user): {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()

    # Return success message
    # 回傳成功訊息
    return JSONResponse(content={"message": "Registration successful",}, status_code=201)


@router.post("/auth/re-passwd", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def reset_password(request: RegisterRequest):
    return JSONResponse(content={"status": "OK"}, status_code=200)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Security(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid authentication credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/auth/test", dependencies=[Depends(RateLimiter(times=60, seconds=300))])
async def protected(current_user: dict = Depends(get_current_user)):
    return JSONResponse(content={"message": "You are authenticated", "user": current_user}, status_code=200)

@router.get("/check_cookie", dependencies=[Depends(RateLimiter(times=60, seconds=300))])
async def check_cookie(request: Request):
    # 從 request 中獲取 cookie
    session_id = request.cookies.get("auth")

    # 如果沒有找到 sessionId，回傳 401 Unauthorized
    if not session_id:
        raise HTTPException(status_code=401, detail="No session cookie found")

    # 驗證 sessionId 是否有效
    is_valid = await verifyCookie(sessionId=session_id)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # 如果驗證通過，返回成功訊息
    return JSONResponse(content={"message": "Session is valid"}, status_code=200)
