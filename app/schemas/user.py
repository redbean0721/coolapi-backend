from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    # full_name: str | None = None

class UserLogin(BaseModel):
    identifier: str  # username or email
    password: str
    totp_code: Optional[str] = None  # 可選的 TOTP 代碼

class ResetPasswordRequest(BaseModel):
    identifier: str # Email or username

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

class ActivateAccount(BaseModel):
    token: str