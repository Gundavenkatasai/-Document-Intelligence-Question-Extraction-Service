from typing import Optional, Dict, Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: Dict[str, Any] = {}


class ReadyResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    storage: bool


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
