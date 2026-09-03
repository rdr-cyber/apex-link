"""Common API response schemas."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: dict  # {"code": "CASE_NOT_FOUND", "message": "..."}


class SuccessResponse(BaseModel):
    message: str
    data: dict | None = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
