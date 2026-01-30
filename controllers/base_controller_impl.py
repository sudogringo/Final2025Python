"""Base controller implementation module with FastAPI dependency injection."""
from typing import Any, Callable, Generic, List, Type, TypeVar
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response # Ensure Response is imported

from schemas.base_schema import BaseSchema
from services.base_service_impl import BaseServiceImpl
from config.database import get_db

T = TypeVar("T", bound=BaseSchema) # Re-bind T to BaseSchema
ServiceType = TypeVar("ServiceType", bound=BaseServiceImpl)


class BaseControllerImpl(Generic[T, ServiceType]):
    """
    Generic and reusable base controller for handling CRUD operations.
    """

    def __init__(
        self,
        schema: Type[T],
        service_factory: Callable[[Session], ServiceType],
        tags: List[str] = None,
        exclude_on_get: set = None
    ):
        self.router = APIRouter(tags=tags)
        self.schema = schema
        self.service_factory = service_factory
        self.exclude_on_get = exclude_on_get

        # Register all CRUD routes
        self._register_routes()

    async def _get_all(self, request: Request, skip: int, limit: int, db: Session):
        service = self.service_factory(db)
        return service.get_all(skip=skip, limit=limit)

    async def _get_one(self, request: Request, id_key: int, db: Session):
        service = self.service_factory(db)
        return service.get_one(id_key)

    async def _create(self, request: Request, schema_in: T, db: Session):
        service = self.service_factory(db)
        try:
            if hasattr(schema_in, "id_key"):
                delattr(schema_in, "id_key")
            return service.save(schema_in)
        except IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate entry: {e.orig}",
            )

    async def _update(self, request: Request, id_key: int, schema_in: T, db: Session):
        service = self.service_factory(db)
        return service.update(id_key, schema_in)

    async def _delete(self, request: Request, id_key: int, db: Session):
        service = self.service_factory(db)
        service.delete(id_key)
        return None


    def _register_routes(self):
        """Register all CRUD routes with proper dependency injection."""

        @self.router.post("/", response_model=self.schema, status_code=status.HTTP_201_CREATED)
        async def create(request: Request, schema_in: self.schema, db: Session = Depends(get_db)): # Reverted schema_in
            return await self._create(request, schema_in, db)

        @self.router.put("/{id_key}", response_model=self.schema, status_code=status.HTTP_200_OK)
        async def update(request: Request, id_key: int, schema_in: self.schema, db: Session = Depends(get_db)): # Reverted schema_in
            return await self._update(request, id_key, schema_in, db)

        @self.router.get("/", response_model=List[self.schema], status_code=status.HTTP_200_OK, response_model_exclude=self.exclude_on_get) # Reverted response_model
        async def get_all(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
            return await self._get_all(request, skip, limit, db)

        @self.router.get("/{id_key}", response_model=self.schema, status_code=status.HTTP_200_OK, response_model_exclude=self.exclude_on_get) # Reverted response_model
        async def get_one(request: Request, id_key: int, db: Session = Depends(get_db)):
            return await self._get_one(request, id_key, db)

        @self.router.delete("/{id_key}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
        async def delete(request: Request, id_key: int, db: Session = Depends(get_db)):
            await self._delete(request, id_key, db)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
