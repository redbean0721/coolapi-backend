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
from datetime import datetime
import os, secrets

from app.utils.otp import generate_totp_secret, verify_totp_code
from app.utils.email_utils import send_email, render_email_template

from app.rate_limiter import limiter
from app.database.redis import redis

from app.routers.user import get_current_user

from app.main import TIMEZONE_NAME

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
    if existing_user:   # 使用者已存在
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")
    
    token = secrets.token_urlsafe(32)
    
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # token 存到 redis, 有效期 24 小時
    await redis.set(f"email_verify:{token}", new_user.id, ex=86400)

    link = f"{API_URL}/account/activate?token={token}"
    html_body = await render_email_template("auth/account_activation.html", {"username": new_user.username, "link": link})
    await send_email(
        to_email=payload.email,
        subject="帳號啟用 / Activate your account",
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
    if not user_id: # 無效或過期的 token
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired activation token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    db_user = result.scalar_one_or_none()
    if not db_user: # 找不到使用者
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db_user.is_active:
        return ORJSONResponse(content={"message": "Account is already activated"})
    
    db_user.is_active = True
    db.add(db_user)
    await db.commit()
    await redis.delete(f"email_verify:{token}")

    html_body = await render_email_template("auth/account_activated.html", {"username": db_user.username, "api_url": API_URL})
    await send_email(
        to_email=db_user.email,
        subject="帳號已啟用 / Account Activated",
        body=html_body,
        subtype="html",
        from_purpose="Account"
    )

    return ORJSONResponse(content={"message": "Account activated successfully"})

# 登入
@router.post("/login")
@limiter.limit("5/minute")  # per IP 限制
@limiter.limit("10/hour")
async def login(request: Request, response: Response, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    # 用 username 或 email 登入
    result = await db.execute(select(User).where(or_(User.username == payload.identifier, User.email == payload.identifier)))
    db_user = result.scalar_one_or_none()
    if not db_user or not verify_password(payload.password, db_user.hashed_password):   # 密碼錯誤
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not db_user.is_active:   # 帳號未啟用
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not activated")
    
    # 有啟用 TOTP，但沒有提供 TOTP code
    if db_user.totp_secret and not payload.totp_code:
        return ORJSONResponse(content={"message": "TOTP code required"}, status_code=status.HTTP_206_PARTIAL_CONTENT)
    
    if db_user.totp_secret:
        if not verify_totp_code(db_user.totp_secret, payload.totp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing TOTP code")

    html_body = await render_email_template("auth/login_notification.html", {"username": db_user.username, "login_time": datetime.now(TIMEZONE_NAME).strftime("%Y-%m-%d %H:%M:%S %Z"), "ip_address": request.client.host, "device_info": request.headers.get("user-agent"), "location": "Unknown"})
    await send_email(
        to_email=db_user.email,
        subject="新登入通知 / New Login Notification",
        body=html_body,
        subtype="html",
        from_purpose="Security"
    )

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
    
    token = secrets.token_urlsafe(32)
    await redis.set(f"reset_password:{token}", db_user.id, ex=3600)  # 1 小時有效

    link = f"{API_URL}/reset-password/confirm?token={token}"
    html_body = await render_email_template("auth/reset_password_request.html", {"username": db_user.username, "ip_address": request.client.host, "link": link})
    await send_email(
        to_email=db_user.email,
        subject="重設密碼 / Reset Password",
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
    if not user_id: # 無效或過期的 token
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user_id = int(user_id)
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user: # 找不到使用者
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    db_user.hashed_password = hash_password(payload.new_password)
    db.add(db_user)
    await db.commit()
    await redis.delete(f"reset_password:{payload.token}")

    # 發送密碼已重設通知郵件
    html_body = await render_email_template("auth/reset_password_successful.html", {"username": db_user.username, "time": datetime.now(TIMEZONE_NAME).strftime("%Y-%m-%d %H:%M:%S %Z"), "ip_address": request.client.host})
    await send_email(
        to_email=db_user.email,
        subject="密碼已重設 / Password Reset Successful",
        body=html_body,
        subtype="html",
        from_purpose="Security"
    )
    return ORJSONResponse(content={"message": "Password reset successfully"})

# 登出
@router.post("/logout")
@limiter.limit("10/minute")
@limiter.limit("30/hour")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token:   # 沒有 session token
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

# 刪除帳號請求
@router.post("/delete-account/request")
@limiter.limit("2/10 minute")
@limiter.limit("5/hour")
async def delete_account_request(request: Request, current_user: User = Depends(get_current_user)):
    token = secrets.token_urlsafe(32)
    await redis.set(f"delete_account:{token}", current_user.id, ex=3600)  # 1 小時有效

    link = f"{API_URL}/auth/delete-account?token={token}"
    html_body = await render_email_template("auth/delete_account_request.html", {"username": current_user.username, "ip_address": request.client.host, "link": link})
    await send_email(
        to_email=current_user.email,
        subject="刪除帳號請求 / Delete Account Request",
        body=html_body,
        subtype="html",
        from_purpose="Account"
    )
    return ORJSONResponse(content={"message": "Account deletion link sent to your email"})

# 確認刪除帳號
@router.post("/delete-account/confirm")
@limiter.limit("2/10 minute")
@limiter.limit("5/hour")
async def delete_account_confirm(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    user_id = await redis.get(f"delete_account:{token}")
    if not user_id: # 無效或過期的 token
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired deletion token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    db_user = result.scalar_one_or_none()
    if not db_user: # 找不到使用者
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    keys = await redis.keys(f"session:*")
    for key in keys:
        session_user_id = await redis.get(key)
        if session_user_id and int(session_user_id) == db_user.id:
            await redis.delete(key)
    
    await db.delete(db_user)
    await db.commit()
    await redis.delete(f"delete_account:{token}")

    html_body = await render_email_template("auth/delete_account_successful.html", {"username": db_user.username})
    await send_email(
        to_email=db_user.email,
        subject="帳號已刪除 / Account Deleted",
        body=html_body,
        subtype="html",
        from_purpose="Account"
    )

    response = ORJSONResponse(content={"message": "Account deleted successfully"})
    session_cookie = request.cookies.get(COOKIE_NAME)
    if session_cookie:
        response.delete_cookie(
            key=COOKIE_NAME,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
        )
    return response