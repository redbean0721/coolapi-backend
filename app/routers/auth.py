from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.mariadb import get_db
from app.database.models import User
from app.utils.hashing import hash_password, verify_password
from app.schemas.user import UserCreate, UserLogin, ResetPasswordRequest, ResetPasswordConfirm
from sqlalchemy.future import select
from sqlalchemy import or_
from app.utils.session import create_session
import os, secrets

from app.utils.otp import generate_totp_secret, verify_totp_code
from app.utils.email_utils import send_email, render_email_template

from app.rate_limiter import limiter
from app.database.redis import redis

from app.routers.user import get_current_user

router = APIRouter()
router.router_name = "auth"
router.prefix = "/auth"

API_URL = os.getenv("API_URL")

from setuptools._distutils.util import strtobool
COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_HTTPONLY = strtobool(os.getenv("COOKIE_HTTPONLY"))
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE"))
COOKIE_PATH = os.getenv("COOKIE_PATH")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")
COOKIE_SECURE = strtobool(os.getenv("COOKIE_SECURE"))
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")

# 註冊
@router.post("/register")
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # 同時檢查 username 和 email 是否存在
    result = await db.execute(select(User).where(or_(User.username == payload.username, User.email == payload.email)))
    # existing_user = result.scalars().first()
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")
    
    email_token = secrets.token_urlsafe(32)
    # totp_secret = generate_totp_secret()
    
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        # is_active=False,
        # totp_secret=totp_secret,
        # totp_secret=None,  # 註冊時不啟用 TOTP
        # email_verify_token=email_token
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # token 存到 redis, 有效期 24 小時
    await redis.set(f"email_verify:{email_token}", new_user.id, ex=86400)

    link = f"{API_URL}/account/activate?token={email_token}"
    html_body = await render_email_template("activate_account.html", {"username": new_user.username, "activation_link": link})
    await send_email(
        to_email=payload.email,
        subject="帳號啟用 / Activate your account",
        # body=f"Please click the following link to activate your account: {link}"
        body=html_body,
        subtype="html",
        from_purpose="Account"
    )
    return ORJSONResponse(content={"message": "User registered successfully. Please check your email to activate your account.", "user_id": new_user.id}, status_code=status.HTTP_201_CREATED)

@router.get("/activate")
@limiter.limit("5/minute")  # per IP 限制
@limiter.limit("10/hour")
async def activate_account(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    user_id = await redis.get(f"email_verify:{token}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token")
    user_id = int(user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db_user.is_active:
        return ORJSONResponse(content={"message": "Account is already activated"})
    
    db_user.is_active = True
    db.add(db_user)
    await db.commit()
    await redis.delete(f"email_verify:{token}")
    return ORJSONResponse(content={"message": "Account activated successfully"})

# 登入
@router.post("/login")
@limiter.limit("5/minute")  # per IP 限制
@limiter.limit("10/hour")
async def login(request: Request, response: Response, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    # 用 username 或 email 登入
    result = await db.execute(select(User).where(or_(User.username == payload.identifier, User.email == payload.identifier)))
    db_user = result.scalar_one_or_none()
    if not db_user or not verify_password(payload.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not db_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not activated")
    
    # 有啟用 TOTP，但沒有提供 TOTP code
    if db_user.totp_secret and not payload.totp_code:
        return ORJSONResponse(content={"message": "TOTP code required"}, status_code=status.HTTP_206_PARTIAL_CONTENT)
    
    if db_user.totp_secret:
        if not verify_totp_code(db_user.totp_secret, payload.totp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing TOTP code")
    
    session_token = await create_session(db_user.id)
    
    response = ORJSONResponse(content={"message": "Login successful", "user_id": db_user.id, "session_token": session_token})
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )
    return response

# 重設密碼, 發送重設連結
@router.post("/reset-password/request")
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def reset_password_request(request: Request, payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(or_(User.email == payload.identifier, User.username == payload.identifier)))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User with this email does not exist")
    
    reset_token = secrets.token_urlsafe(32)
    await redis.set(f"reset_password:{reset_token}", db_user.id, ex=3600)  # 1 小時有效
    # 假設有一個欄位存放重設密碼的 token
    # db_user.reset_password_token = reset_token
    # db.add(db_user)
    # await db.commit()

    link = f"{API_URL}/reset-password/confirm?token={reset_token}"
    html_body = await render_email_template("reset_password.html", {"username": db_user.username, "reset_link": link})
    await send_email(
        to_email=db_user.email,
        subject="重設密碼 / Reset Password",
        # body=f"Please click the following link to reset your password: {link}"
        body=html_body,
        subtype="html",
        from_purpose="Account"
    )
    return ORJSONResponse(content={"message": "Password reset link sent to your email"})

# 確認重設密碼
@router.post("/reset-password/confirm")
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def reset_password_confirm(request: Request, payload: ResetPasswordConfirm, db: AsyncSession = Depends(get_db)):
    user_id = await redis.get(f"reset_password:{payload.token}")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user_id = int(user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    db_user.hashed_password = hash_password(payload.new_password)
    # db_user.reset_password_token = None
    db.add(db_user)
    await db.commit()
    await redis.delete(f"reset_password:{payload.token}")
    return ORJSONResponse(content={"message": "Password reset successfully"})

# 登出
@router.post("/logout")
@limiter.limit("10/minute")
@limiter.limit("30/hour")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    await redis.delete(f"session:{session_token}")
    response = ORJSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )
    return response

# 刪除帳號
@router.delete("/delete-account")
@limiter.limit("2/10 minute")
@limiter.limit("5/hour")
async def delete_account(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.delete(current_user)
    await db.commit()
    # 刪除所有相關的 session
    keys = await redis.keys(f"session:*")
    for key in keys:
        user_id = await redis.get(key)
        if user_id and int(user_id) == current_user.id:
            await redis.delete(key)
    return ORJSONResponse(content={"message": "Account deleted successfully"})