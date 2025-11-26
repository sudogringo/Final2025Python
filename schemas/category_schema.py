"""Category schema with validation."""
from pydantic import Field

from schemas.base_schema import BaseSchema


class CategorySchema(BaseSchema):
    """Schema for Category entity with validations."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name (required, unique)")
