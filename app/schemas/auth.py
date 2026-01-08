from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.schemas.common import ErrorResponse

# 註冊
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: Optional[str] = Field(default=None, max_length=50)
    last_name: Optional[str] = Field(default=None, max_length=50)

class RegisterResponse(BaseModel):
    success: bool = True
    message: str = "Registration successful. Please check your email for a verification link"
    email: EmailStr  # 只返回 email 讓用戶知道郵件發送到哪

REGISTER_DOC = {
    400: {
        "model": ErrorResponse,
        "description": "Username or email already exists",
        "content": {
            "application/json": {
                "examples": {
                    "username_exists": {
                        "summary": "Username already exists",
                        "value": {
                            "success": False,
                            "message": "username already exists",
                            "details": None
                        }
                    },
                    "email_exists": {
                        "summary": "Email already exists",
                        "value": {
                            "success": False,
                            "message": "email already exists",
                            "details": None
                        }
                    }
                }
            }
        }
    }
}

# 啟用帳號
class ActivateResponse(BaseModel):
    success: bool = True
    message: str = "Account activated successfully."

ACTIVATE_DOC = {
    400: {
        "model": ErrorResponse,
        "description": "Invalid or expired token",
        "content": {
            "application/json": {
                "examples": {
                    "Invalid or expired token": {
                        "summary": "Invalid or expired token",
                        "value": {
                            "success": False,
                            "message": "Invalid or expired token",
                            "details": None
                        }
                    },
                    "Account is already activated": {
                        "summary": "Account is already activated",
                        "value": {
                            "success": False,
                            "message": "Account is already activated",
                            "details": None
                        }
                    }
                }
            }
        }
    },
    404: {
        "model": ErrorResponse,
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "User not found",
                    "details": None
                }
            }
        }
    }
}

# 登入
class LoginRequest(BaseModel):
    # username or email
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Login successful."
    # setCookie

LOGIN_DOC = {
    201: {
        "model": ErrorResponse,
        "description": "2FA required",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "2FA required",
                    "details": None
                }
            }
        }
    },
    401: {
        "model": ErrorResponse,
        "description": "Invalid credentials",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Invalid credentials",
                    "details": None
                }
            }
        }
    },
    403: {
        "model": ErrorResponse,
        "description": "Account is not activated",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Account is not activated",
                    "details": "Please check your email for the verification link"
                }
            }
        }
    },
    404: {
        "model": ErrorResponse,
        "description": "User not found",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "User not found",
                    "details": None
                }
            }
        }
    }
}