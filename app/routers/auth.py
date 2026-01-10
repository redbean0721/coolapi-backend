from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.responses import ORJSONResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.mariadb import get_db
from redis.asyncio import Redis
from app.database.modules import User
from app.database.redis import get_redis
from app.schemas.common import ErrorResponse
from app.utils.hashing import hash_password, verify_password
import secrets, rq, os

from app.rate_limiter import limiter

router = APIRouter()
router.router_name = "auth"
router.prefix = "/auth"


from setuptools._distutils.util import strtobool
COOKIE_AUTH_NAME = os.getenv("COOKIE_AUTH_NAME")
COOKIE_2FA_NAME = os.getenv("COOKIE_2FA_NAME")
COOKIE_HTTPONLY = strtobool(os.getenv("COOKIE_HTTPONLY"))
COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE"))
COOKIE_2FA_MAX_AGE = int(os.getenv("COOKIE_2FA_MAX_AGE"))
COOKIE_PATH = os.getenv("COOKIE_PATH")
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")
COOKIE_SECURE = strtobool(os.getenv("COOKIE_SECURE"))
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")


# 註冊
from app.schemas.auth import RegisterRequest, RegisterResponse, REGISTER_DOC
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, response_class=ORJSONResponse, responses=REGISTER_DOC)
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db), redis: Redis=Depends(get_redis)):
    # 檢查 username 和 email 是否已存在
    for field, value in (("username", payload.username), ("email", payload.email)):
        stmt = select(User).where(getattr(User, field) == value)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return ORJSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(message=f"{field} already exists").model_dump()
            )
        
    # 建立新用戶
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 記錄：使用者成功註冊
    await log_and_notify(
        db,
        event_key="register.success",
        user=user,
        request=request,
        message=f"username={user.username}",
        send_email=False
    )

    # 生成一個驗證 token, 並連同 email 給 redis queue 處理發送郵件
    token = secrets.token_urlsafe(32)
    from redis import Redis
    conn = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
    queue = rq.Queue("email", connection=conn)
    job = queue.enqueue("app.tasks.send_verification_email", user.email, token, job_timeout=300)
    print(f"Enqueued job {job.id} to send verification email to {user.email}")

    await redis.setex(f"email_verification:{token}", 3600 * 24, user.id)  # 24 小時內有效

    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=RegisterResponse(email=user.email).model_dump())


# 啟用帳號
from app.schemas.auth import ActivateResponse, ACTIVATE_DOC
@router.get("/activate", response_model=ActivateResponse, status_code=status.HTTP_200_OK, response_class=ORJSONResponse, responses=ACTIVATE_DOC)
@limiter.limit("5/minute")
@limiter.limit("10/hour")
async def activate(request: Request, token: str, db: AsyncSession = Depends(get_db), redis: Redis=Depends(get_redis)):
    user_id = await redis.get(f"email_verification:{token}")
    if not user_id:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message="Invalid or expired token").model_dump()
        )
    
    # 啟用用戶帳號
    stmt = select(User).where(User.id == int(user_id))
    user: User | None = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(message="User not found").model_dump()
        )
    if user.is_active:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message="Account is already activated").model_dump()
        )
    
    user.is_active = True
    db.add(user)
    await db.commit()
    
    # 刪除 redis 中的 token
    await redis.delete(f"email_verification:{token}")
    
    return ORJSONResponse(content=ActivateResponse().model_dump())


# 登入
from app.schemas.auth import LoginRequest, LoginResponse, LOGIN_DOC
from app.utils.session import create_session
from app.utils.jwt import create_jwt_token
from app.utils.audit import log_and_notify
@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK, response_class=ORJSONResponse, responses=LOGIN_DOC)
@limiter.limit("5/minute")
@limiter.limit("10/hour")
async def login(request: Request, payload: LoginRequest, db: AsyncSession=Depends(get_db)):
    # 根據 identifier (username 或 email) 查找用戶
    stmt = select(User).where((User.username == payload.identifier) | (User.email == payload.identifier))
    user: User | None = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        # 記錄：使用者不存在
        await log_and_notify(
            db,
            event_key="login.failed.user_not_found",
            user=None,
            request=request,
            message=f"identifier={payload.identifier}"
        )
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(message="User not found").model_dump()
        )
    if not verify_password(payload.password, user.hashed_password):
        # 記錄並通知：密碼錯誤
        await log_and_notify(
            db,
            event_key="login.failed.invalid_password",
            user=user,
            request=request,
            message="invalid password",
            send_email=True,
            email=user.email,
            email_payload={"reason": "invalid_password"}
        )
        return ORJSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message="Invalid credentials").model_dump()
        )
    
    # 檢查帳號是否啟用
    if not user.is_active:
        # 記錄：帳號未啟用
        await log_and_notify(
            db,
            event_key="login.failed.inactive_account",
            user=user,
            request=request,
            message="inactive account"
        )
        return ORJSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(message="Account is not activated", details="Please check your email for the verification link").model_dump()
        )
    
    # 檢查是否啟用 2FA
    if user.totp_secret:
        # 記錄：需要 2FA
        await log_and_notify(
            db,
            event_key="login.pending.2fa_required",
            user=user,
            request=request
        )
        jwt_token = create_jwt_token({"user_id": user.id, "2fa_required": True}, expires_delta=COOKIE_2FA_MAX_AGE)
        response = ORJSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=ErrorResponse(message="2FA required").model_dump()
        )
        response.set_cookie(
            # 給 2FA 專用的 JWT token
            key=COOKIE_2FA_NAME,
            value=jwt_token,
            max_age=COOKIE_2FA_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
        )
        return response

    # 創建 session 並設置 cookie
    session_token = await create_session(user.id)
    # 記錄並通知：登入成功
    await log_and_notify(
        db,
        event_key="login.success",
        user=user,
        request=request,
        send_email=True,
        email=user.email,
        email_payload={"message": "login_success"}
    )

    response = ORJSONResponse(content=LoginResponse().model_dump())
    response.set_cookie(
        key=COOKIE_AUTH_NAME,
        value=session_token,
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )
    return response


# 2FA 驗證
from fastapi import Cookie, Response
from app.schemas.auth import TwoFARequest, TwoFAResponse, TWO_FA_DOC
from app.utils.jwt import decode_jwt_token
from app.utils.twofa import verify_totp
@router.post("/2fa", response_model=TwoFAResponse, status_code=status.HTTP_200_OK, response_class=ORJSONResponse, responses=TWO_FA_DOC)
@limiter.limit("5/minute")
@limiter.limit("10/hour")
async def two_fa_verify(request: Request, payload: TwoFARequest, auth_2fa_cookie: str | None = Cookie(default=None, alias=COOKIE_2FA_NAME), db: AsyncSession=Depends(get_db)):
    if not auth_2fa_cookie:
        return ORJSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message="2FA cookie missing", details="Please login first").model_dump()
        )
    # 解析 JWT token 獲取 user_id
    try:
        token_data = decode_jwt_token(auth_2fa_cookie)
        if not token_data.get("2fa_required"):
            return ORJSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(message="Invalid authentication token").model_dump()
            )
        user_id = token_data.get("user_id")
    except ValueError as e:
        if str(e) == "Token has expired":
            return ORJSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(message="Authentication token has expired", details="Please login again").model_dump()
            )
        else:
            return ORJSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(message="Invalid authentication token").model_dump()
            )
    
    # 根據 user_id 查找用戶
    stmt = select(User).where(User.id == int(user_id))
    user: User | None = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(message="User not found").model_dump()
        )
    if not user.totp_secret:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message="2FA is not enabled for this account").model_dump()
        )
    
    # 驗證 TOTP token
    if verify_totp(user.totp_secret, payload.totp_code):
        # 創建 session 並設置 cookie
        session_token = await create_session(user.id)
        # 記錄並通知：2FA 驗證成功
        await log_and_notify(
            db,
            event_key="2fa.success",
            user=user,
            request=request,
            send_email=True,
            email=user.email,
            email_payload={"message": "2fa_success"}
        )

        response = ORJSONResponse(content=TwoFAResponse().model_dump())
        response.set_cookie(
            key=COOKIE_AUTH_NAME,
            value=session_token,
            max_age=COOKIE_MAX_AGE,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
            secure=COOKIE_SECURE,
            httponly=COOKIE_HTTPONLY,
            samesite=COOKIE_SAMESITE,
        )
        # 刪除 2FA cookie
        response.delete_cookie(
            key=COOKIE_2FA_NAME,
            path=COOKIE_PATH,
            domain=COOKIE_DOMAIN,
        )
        return response
    else:
        # 記錄並通知：2FA 驗證失敗
        await log_and_notify(
            db,
            event_key="2fa.failed.invalid_code",
            user=user,
            request=request,
            message="invalid 2FA code",
            send_email=True,
            email=user.email,
            email_payload={"reason": "invalid_2fa_code"}
        )
        return ORJSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(message="Invalid 2FA code").model_dump()
        )


# 登出
from fastapi import Cookie, Response
from app.utils.session import delete_session
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, auth_cookie: str | None = Cookie(default=None, alias=COOKIE_AUTH_NAME)):
    if auth_cookie:
        await delete_session(auth_cookie)
    
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=COOKIE_AUTH_NAME,
        path=COOKIE_PATH,
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


# 重設密碼(請求重設, 發送郵件)
from app.utils.utils import mask_email
from app.schemas.auth import PasswordResetRequest, PasswordResetResponse, PASSWORD_RESET_DOC
@router.post("/password-reset/request", response_model=PasswordResetResponse, status_code=status.HTTP_200_OK, response_class=ORJSONResponse, responses=PASSWORD_RESET_DOC)
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def password_reset_request(request: Request, payload: PasswordResetRequest, db: AsyncSession=Depends(get_db), redis: Redis=Depends(get_redis)):
    # 根據 identifier (username 或 email) 查找用戶
    stmt = select(User).where((User.username == payload.identifier) | (User.email == payload.identifier))
    user: User | None = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        # 記錄：使用者不存在
        await log_and_notify(
            db,
            event_key="password_reset_request.failed.user_not_found",
            user=None,
            request=request,
            message=f"identifier={payload.identifier}"
        )
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(message="User not found").model_dump()
        )
    
    # 生成重設密碼 token，存儲在 redis 中, 並連同 email 給 redis queue 處理發送郵件
    token = secrets.token_urlsafe(32)
    await redis.setex(f"password_reset:{token}", 3600, user.id)  # 1 小時內有效
    from redis import Redis
    conn = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
    queue = rq.Queue("email", connection=conn)
    job = queue.enqueue("app.tasks.send_password_reset_email", user.email, token, job_timeout=300)
    print(f"Enqueued job {job.id} to send password reset email to {user.email}")

    # 記錄並通知：重設密碼請求
    await log_and_notify(
        db,
        event_key="password_reset_request.success",
        user=user,
        request=request,
        message="password reset requested",
        send_email=True,
        email=user.email,
        email_payload={"reason": "password_reset_requested"}
    )

    return ORJSONResponse(content=PasswordResetResponse(masked_email=mask_email(user.email)).model_dump())

# 重設密碼(確認重設, 須要 token)
from app.schemas.auth import PasswordResetConfirmRequest, PasswordResetConfirmResponse, PASSWORD_RESET_CONFIRM_DOC
@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse, status_code=status.HTTP_200_OK, response_class=ORJSONResponse, responses=PASSWORD_RESET_CONFIRM_DOC)
@limiter.limit("3/10 minute")
@limiter.limit("6/hour")
async def password_reset_confirm(request: Request, payload: PasswordResetConfirmRequest, db: AsyncSession=Depends(get_db), redis: Redis=Depends(get_redis)):
    user_id = await redis.get(f"password_reset:{payload.token}")
    if not user_id:
        await log_and_notify(
            db,
            event_key="password_reset.failed.invalid_token",
            user=None,
            request=request,
            message="invalid or expired token"
        )
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(message="Invalid or expired token").model_dump()
        )
    
    # 根據 user_id 查找用戶
    stmt = select(User).where(User.id == int(user_id))
    user: User | None = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        await log_and_notify(
            db,
            event_key="password_reset.failed.user_not_found",
            user=None,
            request=request,
            message="user not found for password reset"
        )
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(message="User not found").model_dump()
        )
    
    # 更新用戶密碼
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    await db.commit()
    
    # 刪除 redis 中的 token
    await redis.delete(f"password_reset:{payload.token}")

    # 記錄並通知：密碼重設成功
    await log_and_notify(
        db,
        event_key="password_reset.success",
        user=user,
        request=request,
        message="password has been reset",
        send_email=True,
        email=user.email,
        email_payload={"reason": "password_reset_success"}
    )

    return ORJSONResponse(content=PasswordResetConfirmResponse().model_dump())