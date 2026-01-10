import datetime, jwt, os

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

# 創建 JWT token, 預設過期時間為 5*60 秒
def create_jwt_token(data: dict, expires_delta: int | None = None) -> str:
    """expires_delta: 過期時間(秒)"""
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)  # 必須使用 UTC 時區
    if expires_delta:
        expire = now + datetime.timedelta(seconds=expires_delta)
    else:
        expire = now + datetime.timedelta(minutes=5)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_jwt_token(token: str) -> dict:
    try:
        decoded_payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return decoded_payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")