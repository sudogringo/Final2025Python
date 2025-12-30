"""Unit tests for repository layer."""
import pytest
from datetime import datetime, date

from repositories.base_repository_impl import InstanceNotFoundError
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from repositories.client_repository import ClientRepository
from repositories.address_repository import AddressRepository
from repositories.bill_repository import BillRepository
from repositories.order_repository import OrderRepository
from repositories.order_detail_repository import OrderDetailRepository
from repositories.review_repository import ReviewRepository

from models.category import CategoryModel
from models.product import ProductModel
from models.client import ClientModel
from models.address import AddressModel
from models.bill import BillModel
from models.order import OrderModel
from models.order_detail import OrderDetailModel
from models.review import ReviewModel
from models.enums import DeliveryMethod, Status, PaymentType

from schemas.category_schema import CategorySchema
from schemas.product_schema import ProductSchema
from schemas.client_schema import ClientSchema
from schemas.address_schema import AddressSchema
from schemas.bill_schema import BillSchema
from schemas.order_schema import OrderSchema
from schemas.order_detail_schema import OrderDetailSchema
from schemas.review_schema import ReviewSchema


class TestCategoryRepository:
    """Tests for CategoryRepository."""

    def test_save_category(self, db_session_factory):
        """Test saving a category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)
        category = CategoryModel(name="Electronics")
        saved_category = repo.save(category)
        db_session.commit()

    def test_find_category(self, db_session_factory):
        """Test finding a category by ID."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)
        category = CategoryModel(name="Electronics")
        repo.save(category)
        db_session.commit()
        found_category = repo.find(category.id_key)

    def test_find_category_not_found(self, db_session_factory):
        """Test finding a non-existent category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)

        with pytest.raises(InstanceNotFoundError):
            repo.find(999)

    def test_find_all_categories(self, db_session_factory):
        """Test finding all categories."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)
        repo.save(CategoryModel(name="Electronics"))
        repo.save(CategoryModel(name="Books"))
        db_session.commit()

        result = repo.find_all()

        assert len(result) == 2

    def test_update_category(self, db_session_factory):
        """Test updating a category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)
        category = CategoryModel(name="Electronics")
        saved = repo.save(category)
        db_session.commit()

        result = repo.update(saved.id_key, {"name": "Updated Electronics"})
        db_session.commit()

        assert result.name == "Updated Electronics"

    def test_update_category_not_found(self, db_session_factory):
        """Test updating a non-existent category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)

        with pytest.raises(InstanceNotFoundError):
            repo.update(999, {"name": "Test"})

    def test_remove_category(self, db_session_factory):
        """Test removing a category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)
        category = CategoryModel(name="Electronics")
        saved = repo.save(category)
        db_session.commit()

        repo.remove(saved.id_key)
        db_session.commit()

        with pytest.raises(InstanceNotFoundError):
            repo.find(saved.id_key)

    def test_remove_category_not_found(self, db_session_factory):
        """Test removing a non-existent category."""
        db_session = db_session_factory()
        repo = CategoryRepository(db_session)

        with pytest.raises(InstanceNotFoundError):
            repo.remove(999)


class TestProductRepository:
    """Tests for ProductRepository."""

    def test_save_product(self, db_session_factory):
        """Test saving a product."""
        db_session = db_session_factory()
        category_repo = CategoryRepository(db_session)
        category = CategoryModel(name="Electronics")
        saved_category = category_repo.save(category)
        db_session.commit()

        product_repo = ProductRepository(db_session)
        product = ProductModel(
            name="Laptop",
            price=999.99,
            stock=10,
            category_id=saved_category.id_key
        )
        result = product_repo.save(product)
        db_session.commit()

        assert result.id_key is not None
        assert result.name == "Laptop"
        assert result.price == 999.99
        assert result.stock == 10

    def test_find_product(self, seeded_db):
        """Test finding a product by ID."""
        session = seeded_db["db_session"]
        product_repo = ProductRepository(session)
        product = seeded_db["product"]

        result = product_repo.find(product.id_key)

        assert result.id_key == product.id_key
        assert result.name == "Test Product"

    def test_find_all_products_with_pagination(self, seeded_db):
        """Test finding all products with pagination."""
        session = seeded_db["db_session"]
        product_repo = ProductRepository(session)

        # Add more products
        category = seeded_db["category"]
        for i in range(5):
            product = ProductModel(
                name=f"Product {i}",
                price=100.0 + i,
                stock=i,
                category_id=category.id_key
            )
            product_repo.save(product)
        session.commit() # Commit new products for pagination test

        # Test pagination
        result_page1 = product_repo.find_all(skip=0, limit=3)
        result_page2 = product_repo.find_all(skip=3, limit=3)

        assert len(result_page1) == 3
        assert len(result_page2) == 3

    def test_update_product_stock(self, seeded_db):
        """Test updating product stock."""
        session = seeded_db["db_session"]
        product_repo = ProductRepository(session)
        product = seeded_db["product"]

        result = product_repo.update(product.id_key, {"stock": 20})
        session.commit()

        assert result.stock == 20

    def test_save_all_products(self, db_session_factory):
        """Test saving multiple products."""
        session = db_session_factory()
        category_repo = CategoryRepository(session)
        category = CategoryModel(name="Electronics")
        saved_category = category_repo.save(category)
        session.commit()

        product_repo = ProductRepository(session)
        products = [
            ProductModel(name=f"Product {i}", price=100.0 + i, stock=i, category_id=saved_category.id_key)
            for i in range(3)
        ]

        result = product_repo.save_all(products)
        session.commit()

        assert len(result) == 3
        for i, product in enumerate(result):
            assert product.name == f"Product {i}"


class TestClientRepository:
    """Tests for ClientRepository."""

    def test_save_client(self, db_session_factory):
        """Test saving a client."""
        session = db_session_factory()
        repo = ClientRepository(session)
        client = ClientModel(
            name="John",
            lastname="Doe",
            email="john@example.com",
            telephone="+1234567890"
        )

        result = repo.save(client)
        session.commit()

        assert result.id_key is not None
        assert result.name == "John"
        assert result.lastname == "Doe"
        assert result.email == "john@example.com"

    def test_find_client(self, seeded_db):
        """Test finding a client by ID."""
        session = seeded_db["db_session"]
        repo = ClientRepository(session)
        client = seeded_db["client"]

        result = repo.find(client.id_key)

        assert result.id_key == client.id_key
        assert result.name == "John"
        assert result.lastname == "Doe"

    def test_update_client(self, seeded_db):
        """Test updating a client."""
        session = seeded_db["db_session"]
        repo = ClientRepository(session)
        client = seeded_db["client"]

        new_phone = "+1122334455"
        result = repo.update(client.id_key, {"telephone": new_phone})
        session.commit()

        assert result.telephone == new_phone


class TestAddressRepository:
    """Tests for AddressRepository."""

    def test_save_address(self, seeded_db):
        """Test saving an address."""
        session = seeded_db["db_session"]
        repo = AddressRepository(session)
        client = seeded_db["client"]

        address = AddressModel(
            street="456 Elm St",
            city="Los Angeles",
            client_id=client.id_key
        )

        result = repo.save(address)
        session.commit()

        assert result.id_key is not None
        assert result.street == "456 Elm St"

    def test_find_address(self, seeded_db):
        """Test finding an address by ID."""
        session = seeded_db["db_session"]
        repo = AddressRepository(session)
        address = seeded_db["address"]

        result = repo.find(address.id_key)

        assert result.id_key == address.id_key
        assert result.street == "123 Test St"


class TestBillRepository:
    """Tests for BillRepository."""

    def test_save_bill(self, db_session_factory):
        """Test saving a bill."""
        session = db_session_factory()
        client = ClientModel(name="Test", lastname="Client", email="test@client.com", telephone="1234567")
        session.add(client)
        session.commit()

        repo = BillRepository(session)
        bill = BillModel(
            bill_number="BILL-002",
            discount=5.0,
            date=date.today(),
            total=100.0,
            payment_type=PaymentType.CARD,
            client_id=client.id_key
        )

        result = repo.save(bill)
        session.commit()

        assert result.id_key is not None
        assert result.bill_number == "BILL-002"
        assert result.client_id == client.id_key

    def test_find_bill(self, seeded_db):
        """Test finding a bill by ID."""
        session = seeded_db["db_session"]
        repo = BillRepository(session)
        bill = seeded_db["bill"]

        result = repo.find(bill.id_key)

        assert result.id_key == bill.id_key
        assert result.bill_number == "BILL-TEST-001"

    def test_update_bill_total(self, seeded_db):
        """Test updating bill total."""
        session = seeded_db["db_session"]
        repo = BillRepository(session)
        bill = seeded_db["bill"]

        result = repo.update(bill.id_key, {"total": 1000.0})
        session.commit()

        assert result.total == 1000.0


class TestOrderRepository:
    """Tests for OrderRepository."""

    def test_save_order(self, seeded_db):
        """Test saving an order."""
        session = seeded_db["db_session"]
        repo = OrderRepository(session)
        client = seeded_db["client"]
        bill = seeded_db["bill"]

        order = OrderModel(
            date=datetime.utcnow(),
            total=500.0,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            status=Status.IN_PROGRESS,
            client_id=client.id_key,
            bill_id=bill.id_key
        )

        result = repo.save(order)
        session.commit()

        assert result.id_key is not None
        assert result.total == 500.0
        assert result.delivery_method == DeliveryMethod.HOME_DELIVERY

    def test_find_order(self, seeded_db):
        """Test finding an order by ID."""
        session = seeded_db["db_session"]
        repo = OrderRepository(session)
        order = seeded_db["order"]

        result = repo.find(order.id_key)

        assert result.id_key == order.id_key
        assert result.total == 0.0

    def test_update_order_status(self, seeded_db):
        """Test updating order status."""
        session = seeded_db["db_session"]
        repo = OrderRepository(session)
        order = seeded_db["order"]

        result = repo.update(order.id_key, {"status": Status.DELIVERED})
        session.commit()

        assert result.status == Status.DELIVERED


class TestOrderDetailRepository:
    """Tests for OrderDetailRepository."""

    def test_save_order_detail(self, seeded_db):
        """Test saving an order detail."""
        session = seeded_db["db_session"]
        repo = OrderDetailRepository(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        order_detail = OrderDetailModel(
            quantity=2,
            price=999.99,
            order_id=order.id_key,
            product_id=product.id_key
        )

        result = repo.save(order_detail)
        session.commit()

        assert result.id_key is not None
        assert result.quantity == 2

    def test_find_order_detail(self, seeded_db):
        """Test finding an order detail by ID."""
        session = seeded_db["db_session"]
        repo = OrderDetailRepository(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        # First save an order detail to retrieve it
        order_detail_to_save = OrderDetailModel(
            quantity=1,
            price=10.0,
            order_id=order.id_key,
            product_id=product.id_key
        )
        saved_order_detail = repo.save(order_detail_to_save)
        session.commit() # Ensure it's committed before trying to find it

        result = repo.find(saved_order_detail.id_key)

        assert result.id_key == saved_order_detail.id_key
        assert result.quantity == 1

    def test_update_order_detail_quantity(self, seeded_db):
        """Test updating order detail quantity."""
        session = seeded_db["db_session"]
        repo = OrderDetailRepository(session)
        order = seeded_db["order"]
        product = seeded_db["product"]

        # First save an order detail to update it
        order_detail_to_save = OrderDetailModel(
            quantity=1,
            price=10.0,
            order_id=order.id_key,
            product_id=product.id_key
        )
        saved_order_detail = repo.save(order_detail_to_save)
        session.commit()

        result = repo.update(saved_order_detail.id_key, {"quantity": 3})
        session.commit()

        assert result.quantity == 3


class TestReviewRepository:
    """Tests for ReviewRepository."""

    def test_save_review(self, seeded_db):
        """Test saving a review."""
        session = seeded_db["db_session"]
        repo = ReviewRepository(session)
        product = seeded_db["product"]
        client = seeded_db["client"]

        review = ReviewModel(
            rating=4,
            comment="Good product",
            product_id=product.id_key
        )

        result = repo.save(review)
        session.commit()

        assert result.id_key is not None
        assert result.rating == 4

    def test_find_review(self, seeded_db):
        """Test finding a review by ID."""
        session = seeded_db["db_session"]
        repo = ReviewRepository(session)
        product = seeded_db["product"]
        client = seeded_db["client"]

        # First save a review to retrieve it
        review_to_save = ReviewModel(
            rating=5,
            comment="Excellent product here",
            product_id=product.id_key
        )
        saved_review = repo.save(review_to_save)
        session.commit()

        result = repo.find(saved_review.id_key)

        assert result.id_key == saved_review.id_key
        assert result.rating == 5

    def test_update_review_rating(self, seeded_db):
        """Test updating review rating."""
        session = seeded_db["db_session"]
        repo = ReviewRepository(session)
        product = seeded_db["product"]
        client = seeded_db["client"]

        # First save a review to update it
        review_to_save = ReviewModel(
            rating=4,
            comment="Good product",
            product_id=product.id_key
        )
        saved_review = repo.save(review_to_save)
        session.commit()

        result = repo.update(saved_review.id_key, {"rating": 3, "comment": "This is an average product."})
        session.commit()

        assert result.rating == 3
        assert result.comment == "This is an average product."

    def test_remove_review(self, seeded_db):
        """Test removing a review."""
        session = seeded_db["db_session"]
        repo = ReviewRepository(session)
        product = seeded_db["product"]
        client = seeded_db["client"]

        # First save a review to remove it
        review_to_save = ReviewModel(
            rating=5,
            comment="Excellent product here",
            product_id=product.id_key
        )
        saved_review = repo.save(review_to_save)
        session.commit()

        repo.remove(saved_review.id_key)
        session.commit()

        with pytest.raises(InstanceNotFoundError):
            repo.find(saved_review.id_key)
