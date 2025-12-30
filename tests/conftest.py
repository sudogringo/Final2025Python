# This import is crucial for populating Base.metadata before anything else.
from config import database  # noqa

"""Pytest configuration and fixtures for testing."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime, date
from typing import Generator
from unittest.mock import MagicMock

# Set test environment before importing app modules
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DB'] = 'test_db'
os.environ['POSTGRES_USER'] = 'postgres'
os.environ['POSTGRES_PASSWORD'] = 'postgres'
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'

from config.database import get_db
from models.base_model import base as Base
from main import create_fastapi_app

from models.category import CategoryModel
from models.product import ProductModel
from models.client import ClientModel
from models.address import AddressModel
from models.bill import BillModel
from models.order import OrderModel
from models.review import ReviewModel
from models.enums import Status, DeliveryMethod, PaymentType


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"  # File-based DB for inspection


@pytest.fixture(scope="session")
def engine():
    """Create a new in-memory SQLite engine for each test function."""
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=False
    )
    yield test_engine
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session_factory(engine) -> Generator[sessionmaker, None, None]:
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    try:
        yield SessionLocal
    finally:
        transaction.rollback()
        connection.close()
        Base.metadata.drop_all(bind=engine)  # Drop tables after test


@pytest.fixture(scope="function")
def api_client(db_session_factory: sessionmaker) -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    app = create_fastapi_app()

    def override_get_db():
        session = db_session_factory()
        try:
            yield session
            session.commit() # Commit changes made by the request
        except Exception:
            session.rollback() # Rollback on exception
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


# Model fixtures
@pytest.fixture
def sample_category_data():
    """Sample category data."""
    return {
        "name": "Electronics"
    }


@pytest.fixture
def sample_product_data():
    """Sample product data."""
    return {
        "name": "Laptop",
        "price": 999.99,
        "stock": 10,
        "category_id": 1
    }


@pytest.fixture
def sample_client_data():
    """Sample client data."""
    return {
        "name": "John",
        "lastname": "Doe",
        "email": "john.doe@example.com",
        "telephone": "+1234567890"
    }


@pytest.fixture
def sample_address_data():
    """Sample address data."""
    return {
        "street": "123 Main St",
        "number": "Apt 1",
        "city": "New York",
        "client_id": 1
    }


@pytest.fixture
def sample_bill_data():
    """Sample bill data."""
    return {
        "bill_number": "BILL-001",
        "discount": 10.0,
        "date": date.today(),
        "total": 989.99,
        "payment_type": 1,  # Changed from "cash" to 1 (PaymentType.CASH)
        "client_id": 1  # ✅ Added - required field
    }


@pytest.fixture
def sample_order_data():
    """Sample order data."""
    return {
        "date": datetime.utcnow(),
        "total": 989.99,
        "delivery_method": 1,  # DRIVE_THRU
        "status": 1,  # PENDING
        "client_id": 1,
        "bill_id": 1
    }


@pytest.fixture
def sample_order_detail_data():
    """Sample order detail data."""
    return {
        "quantity": 2,
        "price": 999.99,
        "order_id": 1,
        "product_id": 1
    }


@pytest.fixture
def sample_review_data():
    """Sample review data."""
    return {
        "rating": 4.5,  # Changed to float in range 1.0-5.0
        "comment": "Excellent product, highly recommended!",  # Min 10 chars
        "product_id": 1
    }


# Database seeding fixtures
@pytest.fixture(scope="function")
def seeded_db(db_session_factory: sessionmaker) -> dict:
    session = db_session_factory()
    try:
        # Create a category
        category = CategoryModel(name="Electronics")
        session.add(category)
        session.flush()
        session.refresh(category)

        # Create a product
        product = ProductModel(
            name="Test Product",
            price=10.0,
            stock=100,
            category_id=category.id_key,
        )
        session.add(product)
        session.flush()
        session.refresh(product)

        # Create a client
        client = ClientModel(
            name="John",
            lastname="Doe",
            email="john.doe@example.com",
            telephone="1234567890",
        )
        session.add(client)
        session.flush()
        session.refresh(client)

        # Create an address
        address = AddressModel(
            street="123 Test St",
            city="Testville",
            client_id=client.id_key,
        )
        session.add(address)
        session.flush()
        session.refresh(address)

        # Create a bill
        bill = BillModel(
            bill_number="BILL-TEST-001",
            discount=0.0,
            date=date.today(),
            total=0.0,
            payment_type=PaymentType.CARD,
            client_id=client.id_key
        )
        session.add(bill)
        session.flush()
        session.refresh(bill)

        # Create an order
        order = OrderModel(
            client_id=client.id_key,
            bill_id=bill.id_key,
            status=Status.PENDING,
            delivery_method=DeliveryMethod.DRIVE_THRU,
            date=date.today()
        )
        session.add(order)
        session.flush()
        session.refresh(order)

        # Create a review
        review = ReviewModel(
            product_id=product.id_key,
            rating=4.5,
            comment="Great product!"
        )
        session.add(review)
        session.flush()
        session.refresh(review)

        # No session.commit() here; the overarching transaction from db_session_factory
        # will handle the rollback at the end of the test.
        # The api_client's override_get_db will handle commits for individual requests.

        return {
            "category": category,
            "product": product,
            "client": client,
            "address": address,
            "bill": bill,
            "order": order,
            "review": review,
            "db_session": session # Provide the session for direct use in tests if needed
        }
    finally:
        session.close()


from unittest.mock import MagicMock
@pytest.fixture
def mock_redis():
    """Configures a MagicMock for the Redis client to simulate its behavior."""
    m = MagicMock()
    # Configure the mock to simulate the pipeline behavior
    # When .pipeline() is called, it returns 'm.pipeline.return_value'
    # When .execute() is called on that, it returns a predefined value
    m.pipeline.return_value.execute.return_value = [1, True]  # Default: 1 call, with expiration set
    return m

