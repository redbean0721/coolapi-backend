from fastapi import Depends, APIRouter, Security
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, EmailStr
from src.database.mariadb import get_mariadb_connect
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
    username_or_email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    name_first: str = None  # 如果未提供，則為 None
    name_last: str = None   # 如果未提供，則為 None


async def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

async def generate_jwt_token(user_id: int, username: str, email: str) -> str:
    expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

@router.post("/auth/login", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def auth_login(request: LoginRequest):
    # 檢查 username 或 email 是否存在
    conn, cursor = await get_mariadb_connect()
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (request.username_or_email, request.username_or_email))
        user = cursor.fetchone()  # 使用 fetchone 獲取單條記錄
        if not user:
            raise HTTPException(status_code=404, detail="Invalid username or email")
        
        # 由於使用了字典型游標，這裡可以直接使用字串鍵
        user_id = user['id']
        username = user['username']
        email = user['email']
        hashed_password = user['password']
        # 可以在這裡處理其他欄位（如果需要）
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()
        conn.close()

    # 驗證密碼
    if not await verify_password(request.password, hashed_password):
        raise HTTPException(status_code=403, detail="Invalid password")
    
    # 產生 JWT Token
    token = await generate_jwt_token(user_id, username, email)
    return JSONResponse(content={"message": "Login successful", "token": token}, status_code=200)


@router.post("/auth/register", dependencies=[Depends(RateLimiter(times=15, seconds=300))])
async def auth_register(request: RegisterRequest):
    # Check if the username or email is already taken
    # If not, hash the password and insert the user into the database
    # 檢查 username 或 email 是否已被註冊
    conn, cursor = await get_mariadb_connect()
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (request.username, request.email))
        existing_user = cursor.fetchall()
        if existing_user:
            raise HTTPException(status_code=409, detail="Username or email already exists")
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # Hash the password
    # 加密密碼
    hashed_password = await hash_password(request.password)

    # Set default values for name_first and name_last if not provided
    name_first = request.name_first or request.username
    name_last = request.name_last or request.username

    # Insert the user into the database
    # 將用戶存入資料庫
    try:
        cursor.execute(
            """
            INSERT INTO users (uuid, username, email, password, is_active, name_first, name_last)
            VALUES (UUID(), %s, %s, %s, 1, %s, %s)
            """,
            (request.username, request.email, hashed_password, name_first, name_last)
        )
        conn.commit()  # Commit the transaction
    except Exception as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        cursor.close()
        conn.close()

    # Return success message
    # 回傳成功訊息
    token = await generate_jwt_token(cursor.lastrowid, request.username, request.email)
    return JSONResponse(content={"message": "Registration successful", "token": token}, status_code=201)


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
