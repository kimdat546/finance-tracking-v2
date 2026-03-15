"""Common schema definitions."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

    @property
    def offset(self) -> int:
        """Calculate offset from page number."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


class ErrorResponse(BaseModel):
    """Error response model."""

    status: str = Field(default="error")
    message: str = Field(description="Error message")
    code: str = Field(description="Error code")
    detail: str | None = Field(default=None, description="Additional details")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response."""

    status: str = Field(default="success")
    data: T | None = Field(default=None, description="Response data")
    message: str | None = Field(default=None, description="Success message")
