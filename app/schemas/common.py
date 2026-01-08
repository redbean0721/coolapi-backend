from pydantic import BaseModel
from typing import Optional

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    details: Optional[str] = None