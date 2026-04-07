"""
统一错误码枚举与异常基类。
所有业务异常都继承 AppError，由全局异常处理器统一序列化。
"""
from enum import Enum

from fastapi import HTTPException


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    REVISION_NOT_PENDING = "REVISION_NOT_PENDING"
    SEGMENT_HAS_PENDING_REVISION = "SEGMENT_HAS_PENDING_REVISION"
    SEGMENT_TOO_LONG = "SEGMENT_TOO_LONG"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


class AppError(HTTPException):
    def __init__(self, code: ErrorCode, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.app_message = message
        self.details = details or {}
        super().__init__(status_code=status_code, detail={
            "error": {
                "code": code.value,
                "message": message,
                "details": self.details,
            }
        })
