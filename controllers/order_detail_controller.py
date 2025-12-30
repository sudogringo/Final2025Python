"""OrderDetail controller with proper dependency injection and rate limiting."""
from fastapi import Request, Depends, status
from sqlalchemy.orm import Session
from typing import Any, List
from starlette.responses import Response

from config.database import get_db
from controllers.base_controller_impl import BaseControllerImpl
from schemas.order_detail_schema import OrderDetailSchema
from services.order_detail_service import OrderDetailService
from middleware.endpoint_rate_limiter import order_rate_limit


class OrderDetailController(BaseControllerImpl):
    """
    Controller for OrderDetail entity with CRUD operations.

    Includes endpoint-specific rate limiting to prevent order spam:
    - POST /order_details: Limited to 10 requests per minute per IP
    """

    def __init__(self):
        super().__init__(
            schema=OrderDetailSchema,
            service_factory=lambda db: OrderDetailService(db),
            tags=["Order Details"]
        )

    def _register_routes(self):
        """
        Register OrderDetail routes, applying rate limiting to the create endpoint.
        (Workaround for type errors).
        """
        @self.router.post("/", response_model=None, status_code=status.HTTP_201_CREATED) # Workaround: response_model=None
        @order_rate_limit # Apply the decorator here
        async def create(request: Request, db: Session = Depends(get_db)): # Removed schema_in from signature
            # Manually parse body for now
            schema_in = self.schema(**(await request.json()))
            return await self._create(request, schema_in, db)

        @self.router.put("/{id_key}", response_model=None, status_code=status.HTTP_200_OK) # Workaround: response_model=None
        # @order_rate_limit # Uncomment if update needs rate limiting
        async def update(request: Request, id_key: int, db: Session = Depends(get_db)): # Removed schema_in from signature
            # Manually parse body for now
            schema_in = self.schema(**(await request.json()))
            return await self._update(request, id_key, schema_in, db)

        @self.router.get("/", response_model=None, status_code=status.HTTP_200_OK) # Workaround: response_model=None
        async def get_all(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
            return await self._get_all(request, skip, limit, db)

        @self.router.get("/{id_key}", response_model=None, status_code=status.HTTP_200_OK) # Workaround: response_model=None
        async def get_one(request: Request, id_key: int, db: Session = Depends(get_db)):
            return await self._get_one(request, id_key, db)

        @self.router.delete("/{id_key}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
        async def delete(request: Request, id_key: int, db: Session = Depends(get_db)):
            await self._delete(request, id_key, db)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    async def _create( # This is the internal method for core logic
        self,
        request: Request,
        schema_in: OrderDetailSchema, # Keep explicit schema type here for internal logic
        db: Session
    ):
        """
        Internal method to create a new order detail.
        """
        service = self.service_factory(db)
        return service.save(schema_in)

    async def _update( # Adding missing _update method to match overridden update route
        self,
        request: Request,
        id_key: int,
        schema_in: OrderDetailSchema, # Keep explicit schema type here for internal logic
        db: Session
    ):
        """
        Internal method to update an order detail.
        """
        service = self.service_factory(db)
        return service.update(id_key, schema_in)