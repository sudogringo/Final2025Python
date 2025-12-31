# This import is crucial for populating Base.metadata before anything else.
from config import database  # noqa

"""Pytest configuration and fixtures for testing."""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from datetime import datetime, date
from typing import Generator, Any
from unittest.mock import MagicMock, patch
import collections # Import collections for deque

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
def api_client(db_session_factory: sessionmaker, mock_redis: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    mock_redis.reset_store() # Reset Redis mock state for each test function
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

    # Patch get_redis_client to return our mock
    from config import redis_config # Import redis_config to patch its get_client method
    with patch.object(redis_config.redis_config, 'get_client', return_value=mock_redis):
        with TestClient(app, cookies={}) as test_client:
            yield test_client


# Removed TimeSequenceCallable as it's no longer needed for this approach.

@pytest.fixture(scope="function")
def client_with_time_mock(db_session_factory: sessionmaker, mock_redis: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    mock_redis.reset_store() # Reset Redis mock state for each test function
    
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

    # Patch get_redis_client to return our mock
    from config import redis_config # Import redis_config to patch its get_client method
    with patch.object(redis_config.redis_config, 'get_client', return_value=mock_redis):
        with TestClient(app, cookies={}) as test_client:
            # test_client.mock_time is no longer exposed here
            # test_client.time_sequencer is no longer exposed here
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


@pytest.fixture
def mock_redis():
    """Configures a MagicMock for the Redis client to simulate its behavior."""
    _redis_store = {}

    def mock_get(key):
        return _redis_store.get(key)

    def mock_incr(key):
        _redis_store[key] = int(_redis_store.get(key) or 0) + 1
        return _redis_store[key]

    def mock_set(key, value):
        _redis_store[key] = value

    def mock_expire(key, time):
        return True

    def mock_ttl(key):
        return 60

    m = MagicMock()
    m.get.side_effect = mock_get
    m.incr.side_effect = mock_incr
    m.set.side_effect = mock_set
    m.expire.side_effect = mock_expire
    m.ttl.side_effect = mock_ttl
    m.ping.return_value = True

    # Mock pipeline behavior
    pipeline_mock = MagicMock()

    # Store commands in a list
    _pipeline_commands = []

    def _pipeline_incr(key):
        _pipeline_commands.append(("incr", key))

    def _pipeline_expire(key, time):
        _pipeline_commands.append(("expire", key, time))

    def _pipeline_execute():
        results = []
        for cmd in _pipeline_commands:
            if cmd[0] == "incr":
                results.append(mock_incr(cmd[1]))
            elif cmd[0] == "expire":
                results.append(mock_expire(cmd[1], cmd[2]))
        _pipeline_commands.clear()
        return results

    pipeline_mock.incr.side_effect = _pipeline_incr
    pipeline_mock.expire.side_effect = _pipeline_expire
    pipeline_mock.execute.side_effect = _pipeline_execute
    m.pipeline.return_value = pipeline_mock

    def reset_store():
        _redis_store.clear()
        _pipeline_commands.clear()
    m.reset_store = reset_store

    return m
