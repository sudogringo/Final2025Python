"""Unit tests for service layer with business logic validation."""
import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch

from repositories.base_repository_impl import InstanceNotFoundError
from services.category_service import CategoryService
from services.product_service import ProductService
from services.client_service import ClientService
from services.address_service import AddressService
from services.bill_service import BillService
from services.order_service import OrderService
from services.order_detail_service import OrderDetailService
from services.review_service import ReviewService

from schemas.category_schema import CategorySchema
from schemas.product_schema import ProductSchema
from schemas.client_schema import ClientSchema
from schemas.address_schema import AddressSchema
from schemas.bill_schema import BillSchema
from schemas.order_schema import OrderSchema
from schemas.order_detail_schema import OrderDetailSchema
from schemas.review_schema import ReviewSchema

from models.enums import DeliveryMethod, Status, PaymentType
from models.order_detail import OrderDetailModel


class TestCategoryService:
    """Tests for CategoryService."""

    def test_get_all_categories(self, db_session_factory, seeded_db):
        """Test getting all categories."""
        session = db_session_factory()
        service = CategoryService(session)
        result = service.get_all()

        assert len(result) > 0
        assert any(c.name == "Electronics" for c in result)

    def test_get_one_category(self, db_session_factory, seeded_db):
        """Test getting a single category."""
        session = db_session_factory()
        service = CategoryService(session)
        category = seeded_db["category"]

        result = service.get_one(category.id_key)

        assert result.id_key == category.id_key
        assert result.name == "Electronics"

    def test_save_category(self, db_session_factory):
        """Test saving a new category."""
        session = db_session_factory()
        service = CategoryService(session)
        schema = CategorySchema(name="Books")

        result = service.save(schema)

        assert result.id_key is not None
        assert result.name == "Books"

    def test_update_category(self, db_session_factory, seeded_db):
        """Test updating a category."""
        session = db_session_factory()
        service = CategoryService(session)
        category = seeded_db["category"]
        schema = CategorySchema(name="Updated Electronics")

        result = service.update(category.id_key, schema)

        assert result.name == "Updated Electronics"

    def test_delete_category(self, db_session_factory, seeded_db):
        """Test deleting a category."""
        session = db_session_factory()
        service = CategoryService(session)
        # Create a new category without products
        schema = CategorySchema(name="Temporary")
        saved = service.save(schema)

        service.delete(saved.id_key)

        with pytest.raises(InstanceNotFoundError):
            service.get_one(saved.id_key)


class TestProductService:
    """Tests for ProductService."""

    def test_get_all_products(self, db_session_factory, seeded_db):
        """Test getting all products."""
        session = db_session_factory()
        service = ProductService(session)
        result = service.get_all()

        assert len(result) > 0
        assert any(p.name == "Test Product" for p in result)

    def test_save_product(self, db_session_factory, seeded_db):
        """Test saving a new product."""
        session = db_session_factory()
        service = ProductService(session)
        category = seeded_db["category"]

        schema = ProductSchema(
            name="Mouse",
            price=29.99,
            stock=50,
            category_id=category.id_key
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.name == "Mouse"
        assert result.price == 29.99
        assert result.stock == 50

    def test_update_product_stock(self, db_session_factory, seeded_db):
        """Test updating product stock."""
        session = db_session_factory()
        service = ProductService(session)
        product = seeded_db["product"]

        schema = ProductSchema(
            name=product.name,
            price=product.price,
            stock=20,
            category_id=product.category_id
        )

        result = service.update(product.id_key, schema)

        assert result.stock == 20


class TestClientService:
    """Tests for ClientService."""

    def test_save_client(self, db_session_factory):
        """Test saving a new client."""
        session = db_session_factory()
        service = ClientService(session)
        schema = ClientSchema(
            name="Jane",
            lastname="Smith",
            email="jane@example.com",
            telephone="+9876543210"
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.name == "Jane"
        assert result.lastname == "Smith"
        assert result.email == "jane@example.com"

    def test_get_one_client(self, db_session_factory, seeded_db):
        """Test getting a single client."""
        session = db_session_factory()
        service = ClientService(session)
        client = seeded_db["client"]

        result = service.get_one(client.id_key)

        assert result.id_key == client.id_key
        assert result.name == "John"
        assert result.lastname == "Doe"


class TestOrderService:
    """Tests for OrderService with FK validation."""

    def test_save_order_success(self, db_session_factory, seeded_db):
        """Test saving an order with valid references."""
        session = db_session_factory()
        service = OrderService(session)
        client = seeded_db["client"]
        bill = seeded_db["bill"]

        schema = OrderSchema(
            order_date=datetime.utcnow(),
            total=500.0,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            status=Status.PENDING,
            client_id=client.id_key,
            bill_id=bill.id_key
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.total == 500.0
        assert result.client_id == client.id_key

    def test_save_order_invalid_client(self, db_session_factory, seeded_db):
        """Test saving an order with invalid client ID."""
        session = db_session_factory()
        service = OrderService(session)
        bill = seeded_db["bill"]

        schema = OrderSchema(
            order_date=datetime.utcnow(),
            total=500.0,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            status=Status.PENDING,
            client_id=9999,  # Non-existent client
            bill_id=bill.id_key
        )

        with pytest.raises(InstanceNotFoundError) as exc_info:
            service.save(schema)

        assert "Client with id 9999 not found" in str(exc_info.value)

    def test_save_order_invalid_bill(self, db_session_factory, seeded_db):
        """Test saving an order with invalid bill ID."""
        session = db_session_factory()
        service = OrderService(session)
        client = seeded_db["client"]

        schema = OrderSchema(
            order_date=datetime.utcnow(),
            total=500.0,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            status=Status.PENDING,
            client_id=client.id_key,
            bill_id=9999  # Non-existent bill
        )

        with pytest.raises(InstanceNotFoundError) as exc_info:
            service.save(schema)

        assert "Bill with id 9999 not found" in str(exc_info.value)

    def test_save_order_auto_date(self, db_session_factory, seeded_db):
        """Test that order date is auto-set if not provided."""
        session = db_session_factory()
        service = OrderService(session)
        client = seeded_db["client"]
        bill = seeded_db["bill"]

        schema = OrderSchema(
            total=500.0,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            status=Status.PENDING,
            client_id=client.id_key,
            bill_id=bill.id_key
        )

        result = service.save(schema)

        assert result.date is not None
        assert isinstance(result.date, datetime)

    def test_update_order_with_valid_client(self, db_session_factory, seeded_db):
        """Test updating order with valid client reference."""
        session = db_session_factory()
        service = OrderService(session)
        order = seeded_db["order"]
        client = seeded_db["client"]

        schema = OrderSchema(
            date=order.date,
            total=1000.0,
            delivery_method=order.delivery_method,
            status=Status.IN_PROGRESS,
            client_id=client.id_key,
            bill_id=order.bill_id
        )

        result = service.update(order.id_key, schema)

        assert result.total == 1000.0
        assert result.status == Status.IN_PROGRESS


class TestOrderDetailService:
    """Tests for OrderDetailService with stock management."""

    def test_save_order_detail_success(self, db_session_factory, seeded_db):
        """Test saving an order detail with sufficient stock."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        initial_stock = product.stock

        schema = OrderDetailSchema(
            quantity=2,
            price=product.price,
            order_id=order.id_key,
            product_id=product.id_key
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.quantity == 2

        # Verify stock was deducted
        from services.product_service import ProductService
        product_service = ProductService(session)
        updated_product = product_service.get_one(product.id_key)
        assert updated_product.stock == initial_stock - 2

    def test_save_order_detail_insufficient_stock(self, db_session_factory, seeded_db):
        """Test saving an order detail with insufficient stock."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        schema = OrderDetailSchema(
            quantity=999,  # More than available stock
            price=product.price,
            order_id=order.id_key,
            product_id=product.id_key
        )

        with pytest.raises(ValueError) as exc_info:
            service.save(schema)

        assert "Insufficient stock" in str(exc_info.value)

    def test_save_order_detail_price_mismatch(self, db_session_factory, seeded_db):
        """Test saving an order detail with incorrect price."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        schema = OrderDetailSchema(
            quantity=1,
            price=100.0,  # Different from product price
            order_id=order.id_key,
            product_id=product.id_key
        )

        with pytest.raises(ValueError) as exc_info:
            service.save(schema)

        assert "Price mismatch" in str(exc_info.value)

    def test_save_order_detail_auto_price(self, db_session_factory, seeded_db):
        """Test that price is auto-set from product if not provided."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        schema = OrderDetailSchema(
            quantity=1,
            order_id=order.id_key,
            product_id=product.id_key
        )

        result = service.save(schema)

        assert result.price == product.price

    def test_save_order_detail_invalid_order(self, db_session_factory, seeded_db):
        """Test saving an order detail with invalid order ID."""
        session = db_session_factory()
        service = OrderDetailService(session)
        product = seeded_db["product"]

        schema = OrderDetailSchema(
            quantity=1,
            price=product.price,
            order_id=9999,  # Non-existent order
            product_id=product.id_key
        )

        with pytest.raises(InstanceNotFoundError) as exc_info:
            service.save(schema)

        assert "OrderModel with id 9999 not found" in str(exc_info.value)

    def test_save_order_detail_invalid_product(self, db_session_factory, seeded_db):
        """Test saving an order detail with invalid product ID."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]

        schema = OrderDetailSchema(
            quantity=1,
            price=100.0,
            order_id=order.id_key,
            product_id=9999  # Non-existent product
        )

        with pytest.raises(InstanceNotFoundError) as exc_info:
            service.save(schema)

        assert "Product with id 9999 not found" in str(exc_info.value)

    def test_delete_order_detail_restores_stock(self, db_session_factory, seeded_db):
        """Test that deleting an order detail restores stock."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        # Create order detail
        schema = OrderDetailSchema(
            quantity=2,
            price=product.price,
            order_id=order.id_key,
            product_id=product.id_key
        )
        created = service.save(schema)

        # Get stock after creation
        from services.product_service import ProductService
        product_service = ProductService(session)
        updated_product = product_service.get_one(product.id_key)
        stock_after_create = updated_product.stock

        # Delete order detail
        service.delete(created.id_key)

        # Verify stock was restored
        product_after_delete = product_service.get_one(product.id_key)
        assert product_after_delete.stock == stock_after_create + 2

    def test_update_order_detail_quantity_increase(self, db_session_factory, seeded_db):
        """Test updating order detail with quantity increase."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        # First create an order detail
        initial_quantity = 1
        order_detail_to_save = OrderDetailModel(
            quantity=initial_quantity,
            price=product.price,
            order_id=order.id_key,
            product_id=product.id_key
        )
        created_order_detail = service.save(OrderDetailSchema.model_validate(order_detail_to_save))

        schema = OrderDetailSchema(
            quantity=initial_quantity + 1,
            price=created_order_detail.price,
            order_id=created_order_detail.order_id,
            product_id=created_order_detail.product_id
        )

        # This should succeed if there's enough stock
        if product.stock >= 1: # Assumes initial product stock is > 0
            result = service.update(created_order_detail.id_key, schema)
            assert result.quantity == initial_quantity + 1

    def test_update_order_detail_quantity_decrease(self, db_session_factory, seeded_db):
        """Test updating order detail with quantity decrease."""
        session = db_session_factory()
        service = OrderDetailService(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        # Create order detail with quantity 3
        schema = OrderDetailSchema(
            quantity=3,
            price=product.price,
            order_id=order.id_key,
            product_id=product.id_key
        )
        created = service.save(schema)

        # Get stock after creation
        from services.product_service import ProductService
        product_service = ProductService(session)
        product_after_create = product_service.get_one(product.id_key)
        stock_after_create = product_after_create.stock

        # Decrease quantity to 1
        update_schema = OrderDetailSchema(
            quantity=1,
            price=created.price,
            order_id=created.order_id,
            product_id=created.product_id
        )
        result = service.update(created.id_key, update_schema)

        assert result.quantity == 1

        # Verify stock was restored by 2
        product_after_update = product_service.get_one(product.id_key)
        assert product_after_update.stock == stock_after_create + 2


class TestBillService:
    """Tests for BillService."""

    def test_save_bill(self, db_session_factory, seeded_db):
        """Test saving a new bill."""
        session = db_session_factory()
        client = seeded_db["client"]
        service = BillService(session)
        schema = BillSchema(
            bill_number=f"BILL-TEST-SERVICES-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            discount=15.0,
            date=date.today(),
            total=850.0,
            payment_type=PaymentType.CARD,
            client_id=client.id_key
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.bill_number.startswith("BILL-TEST-SERVICES-")
        assert result.total == 850.0
        assert result.client_id == client.id_key

    def test_update_bill(self, db_session_factory, seeded_db):
        """Test updating a bill."""
        session = db_session_factory()
        service = BillService(session)
        bill = seeded_db["bill"]

        schema = BillSchema(
            bill_number=bill.bill_number,
            discount=20.0,
            date=bill.date,
            total=900.0,
            payment_type=bill.payment_type,
            client_id=bill.client_id
        )

        result = service.update(bill.id_key, schema)

        assert result.discount == 20.0
        assert result.total == 900.0


class TestAddressService:
    """Tests for AddressService."""

    def test_save_address(self, db_session_factory, seeded_db):
        """Test saving a new address."""
        session = db_session_factory()
        service = AddressService(session)
        client = seeded_db["client"]

        schema = AddressSchema(
            street="789 Oak Ave",
            city="Chicago",
            client_id=client.id_key
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.street == "789 Oak Ave"


class TestReviewService:
    """Tests for ReviewService."""

    def test_save_review(self, db_session_factory, seeded_db):
        """Test saving a new review."""
        session = db_session_factory()
        service = ReviewService(session)
        product = seeded_db["product"]
        client = seeded_db["client"]

        schema = ReviewSchema(
            rating=4,
            comment="Good value for money",
            product_id=product.id_key,
            client_id=client.id_key # Add client_id
        )

        result = service.save(schema)

        assert result.id_key is not None
        assert result.rating == 4
        assert result.comment == "Good value for money"

    def test_update_review(self, db_session_factory, seeded_db):
        """Test updating a review."""
        session = db_session_factory()
        service = ReviewService(session)
        review = seeded_db["review"]

        schema = ReviewSchema(
            rating=4,
            comment="Updated comment",
            product_id=review.product_id
        )

        result = service.update(review.id_key, schema)

        assert result.rating == 4
        assert result.comment == "Updated comment"
