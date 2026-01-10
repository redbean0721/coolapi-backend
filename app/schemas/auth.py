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

# 2FA 驗證
class TwoFARequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit TOTP code")

class TwoFAResponse(BaseModel):
    success: bool = True
    message: str = "2FA verification successful"
    # setCookie

TWO_FA_DOC = {
    400: {
        "model": ErrorResponse,
        "description": "User does not have 2FA enabled",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "2FA is not enabled for this account",
                    "details": None
                }
            }
        }
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication failed - invalid JWT cookie, expired token, or incorrect TOTP code",
        "content": {
            "application/json": {
                "examples": {
                    "missing_cookie": {
                        "summary": "Missing 2FA JWT cookie",
                        "value": {
                            "success": False,
                            "message": "2FA cookie missing",
                            "details": "Please login first"
                        }
                    },
                    "invalid_jwt": {
                        "summary": "Invalid or malformed JWT token",
                        "value": {
                            "success": False,
                            "message": "Invalid authentication token",
                            "details": None
                        }
                    },
                    "expired_jwt": {
                        "summary": "JWT token expired",
                        "value": {
                            "success": False,
                            "message": "Authentication token expired",
                            "details": "Please login again"
                        }
                    },
                    "invalid_totp": {
                        "summary": "Incorrect TOTP code",
                        "value": {
                            "success": False,
                            "message": "Invalid 2FA code",
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

# 重設密碼請求
class PasswordResetRequest(BaseModel):
    # username or email
    identifier: str = Field(min_length=3, max_length=255)

class PasswordResetResponse(BaseModel):
    success: bool = True
    message: str = "Password reset email has been sent"
    masked_email: str  # Masked email format, e.g., redbean0721@gmail.com -> re****@gm****.com

PASSWORD_RESET_DOC = {
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

# 重設密碼
class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)

class PasswordResetConfirmResponse(BaseModel):
    success: bool = True
    message: str = "Password has been reset successfully"

PASSWORD_RESET_CONFIRM_DOC = {
    400: {
        "model": ErrorResponse,
        "description": "Invalid or expired token",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Invalid or expired token",
                    "details": None
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
# 2FA 驗證
class Verify2FARequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit TOTP code")

class Verify2FAResponse(BaseModel):
    success: bool = True
    message: str = "2FA verification successful"

VERIFY_2FA_DOC = {
    400: {
        "model": ErrorResponse,
        "description": "Invalid request or user does not have 2FA enabled",
        "content": {
            "application/json": {
                "examples": {
                    "no_2fa": {
                        "summary": "User does not have 2FA enabled",
                        "value": {
                            "success": False,
                            "message": "2FA is not enabled for this account",
                            "details": None
                        }
                    },
                    "invalid_format": {
                        "summary": "Invalid TOTP code format",
                        "value": {
                            "success": False,
                            "message": "Invalid TOTP code format",
                            "details": "TOTP code must be 6 digits"
                        }
                    }
                }
            }
        }
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication failed - invalid JWT cookie, expired token, or incorrect TOTP code",
        "content": {
            "application/json": {
                "examples": {
                    "missing_cookie": {
                        "summary": "Missing 2FA JWT cookie",
                        "value": {
                            "success": False,
                            "message": "2FA cookie not found",
                            "details": "Please login first"
                        }
                    },
                    "invalid_jwt": {
                        "summary": "Invalid or malformed JWT token",
                        "value": {
                            "success": False,
                            "message": "Invalid authentication token",
                            "details": None
                        }
                    },
                    "expired_jwt": {
                        "summary": "JWT token expired",
                        "value": {
                            "success": False,
                            "message": "Authentication token expired",
                            "details": "Please login again"
                        }
                    },
                    "invalid_totp": {
                        "summary": "Incorrect TOTP code",
                        "value": {
                            "success": False,
                            "message": "Invalid 2FA code",
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
