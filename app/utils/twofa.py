import pyotp

def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
    """Verify TOTP token using the provided secret."""
    return pyotp.TOTP(secret).verify(token, valid_window=valid_window)