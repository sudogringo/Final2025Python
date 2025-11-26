"""Base controller implementation module with FastAPI dependency injection."""
from typing import Any, Callable, Dict, List, Set, Type, Union

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from config.database import get_db
from controllers.base_controller import BaseController
from schemas.base_schema import BaseSchema


class BaseControllerImpl(BaseController):
    """
    Base controller implementation using FastAPI dependency injection.

    This class creates standard CRUD endpoints and properly manages database sessions.
    """

    def __init__(
        self,
        schema: Type[BaseSchema],
        service_factory: Callable[[Session], 'BaseService'],
        tags: List[str] = None,
        exclude_on_get: Union[Set[str], Dict[str, Any]] = None,
    ):
        """
        Initialize the controller with dependency injection support.

        Args:
            schema: The Pydantic schema class for validation
            service_factory: A callable that creates a service instance given a DB session
            tags: Optional list of tags for API documentation
            exclude_on_get: A set or dict of field names to exclude from the response on get requests
        """
        self.schema = schema
        self.service_factory = service_factory
        self.router = APIRouter(tags=tags or [])
        self.exclude_on_get = exclude_on_get

        # Register all CRUD endpoints with proper dependency injection
        self._register_routes()

    def _register_routes(self):
        """Register all CRUD routes with proper dependency injection."""

        @self.router.get(
            "/",
            response_model=List[self.schema],
            status_code=status.HTTP_200_OK,
            response_model_exclude=self.exclude_on_get,
        )
        async def get_all(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
            """Get all records with pagination."""
            service = self.service_factory(db)
            return service.get_all(skip=skip, limit=limit)

        @self.router.get(
            "/{id_key}",
            response_model=self.schema,
            status_code=status.HTTP_200_OK,
            response_model_exclude=self.exclude_on_get,
        )

        @self.router.post("/", response_model=self.schema, status_code=status.HTTP_201_CREATED)
        async def create(
            schema_in: self.schema,
            db: Session = Depends(get_db)
        ):
            """Create a new record."""
            service = self.service_factory(db)
            return service.save(schema_in)

        @self.router.put("/{id_key}", response_model=self.schema, status_code=status.HTTP_200_OK)
        async def update(
            id_key: int,
            schema_in: self.schema,
            db: Session = Depends(get_db)
        ):
            """Update an existing record."""
            service = self.service_factory(db)
            return service.update(id_key, schema_in)

        @self.router.delete("/{id_key}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete(
            id_key: int,
            db: Session = Depends(get_db)
        ):
            """Delete a record."""
            service = self.service_factory(db)
            service.delete(id_key)
            return None
