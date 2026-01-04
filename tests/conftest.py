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
import time # New import
import re   # New import

# Set test environment before importing app modules
os.environ['DATABASE_URL'] = 'sqlite:///:memory:' # Use in-memory SQLite for tests
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ["DISABLE_RATE_LIMITER_FOR_TESTS"] = "true"

# This import is crucial for populating Base.metadata before anything else.
# It must come AFTER environment variables are set for the database.
from config import database  # noqa

# Autouse fixture to disable file logging during tests
@pytest.fixture(autouse=True, scope="session")
def _disable_file_logging():
    from unittest.mock import patch
    from config.logging_config import LOGGING_CONFIG

    original_root_handlers = list(LOGGING_CONFIG['root']['handlers'])
    original_uvicorn_error_handlers = list(LOGGING_CONFIG['loggers']['uvicorn.error']['handlers'])
    original_sqlalchemy_engine_handlers = list(LOGGING_CONFIG['loggers']['sqlalchemy.engine']['handlers'])

    # Patch the LOGGING_CONFIG to remove file handlers
    # Using a deepcopy to avoid modifying the original dictionary that might be used elsewhere
    with patch('main.setup_logging'), \
         patch.dict(LOGGING_CONFIG['root'], {'handlers': ['console']}), \
         patch.dict(LOGGING_CONFIG['loggers']['uvicorn.error'], {'handlers': ['console']}), \
         patch.dict(LOGGING_CONFIG['loggers']['sqlalchemy.engine'], {'handlers': ['console']}):
        yield

    # Restore original handlers
    LOGGING_CONFIG['root']['handlers'] = original_root_handlers
    LOGGING_CONFIG['loggers']['uvicorn.error']['handlers'] = original_uvicorn_error_handlers
    LOGGING_CONFIG['loggers']['sqlalchemy.engine']['handlers'] = original_sqlalchemy_engine_handlers

from config.database import get_db
from models.base_model import base as Base
from models.category import CategoryModel
from models.product import ProductModel
from models.client import ClientModel
from models.address import AddressModel
from models.bill import BillModel
from models.order import OrderModel
from models.review import ReviewModel
from models.enums import Status, DeliveryMethod, PaymentType


# Test database URL
TEST_DATABASE_URL = "sqlite:///:memory:"  # In-memory DB for test isolation


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
    
    from main import create_fastapi_app
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

    from config import redis_config
    with patch.object(redis_config.redis_config, 'get_client', return_value=mock_redis):
        with TestClient(app, cookies={}) as test_client:
            yield test_client


@pytest.fixture(scope="function")
def client_with_time_mock(db_session_factory: sessionmaker, mock_redis: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    mock_redis.reset_store() # Reset Redis mock state for each test function
    
    from main import create_fastapi_app
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

    from config import redis_config
    with patch.object(redis_config.redis_config, 'get_client', return_value=mock_redis):
        with TestClient(app, cookies={}) as test_client:
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
    _expirations = {} # To simulate TTL

    def mock_get(key):
        # Simulate expiration
        if key in _expirations and _expirations[key] <= time.time():
            del _redis_store[key]
            del _expirations[key]
            return None
        return _redis_store.get(key)

    def mock_incr(key):
        _redis_store[key] = int(_redis_store.get(key, 0)) + 1 # Use default 0 for get
        if key not in _expirations: # Set default expiry if not already set by EXPIRE command
             _expirations[key] = time.time() + 60 # Default 60s
        return _redis_store[key]

    def mock_set(key, value, ex=None): # Add ex parameter for expiration
        _redis_store[key] = value
        if ex is not None:
            _expirations[key] = time.time() + ex
        else:
            _expirations.pop(key, None) # Remove expiration if not set
        return True

    def mock_setex(key, time_val, value): # Add setex to mock
        _redis_store[key] = value
        _expirations[key] = time.time() + time_val
        return True

    def mock_expire(key, time_val): # time is a keyword, use time_val
        if key in _redis_store:
            _expirations[key] = time.time() + time_val
            return True
        return False

    def mock_ttl(key):
        if key in _expirations:
            remaining_ttl = int(_expirations[key] - time.time())
            return max(-2, remaining_ttl) # -2 for key not exist, -1 for no expire
        return -2 # Key does not exist

    def mock_delete(*keys_to_delete): # Support multiple keys
        deleted_count = 0
        for key in keys_to_delete:
            if key in _redis_store:
                del _redis_store[key]
                _expirations.pop(key, None)
                deleted_count += 1
        return deleted_count

    def mock_keys(pattern):
        import re
        # Convert glob pattern to regex for matching
        # Redis glob patterns: * matches any sequence of characters, ? matches any single character
        # Regex equivalent: .* for *, .? for ?, escape other special regex chars
        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
        # Ensure it matches the whole key
        regex = re.compile(f"^{regex_pattern}$")
        
        matched_keys = []
        for key in _redis_store.keys():
            if regex.match(key):
                matched_keys.append(key)
        return matched_keys


    m = MagicMock()
    m.get.side_effect = mock_get
    m.incr.side_effect = mock_incr
    m.set.side_effect = mock_set
    m.setex.side_effect = mock_setex # Add setex
    m.expire.side_effect = mock_expire
    m.ttl.side_effect = mock_ttl
    m.ping.return_value = True
    m.delete.side_effect = mock_delete # Add delete method
    m.keys.side_effect = mock_keys # Add keys method
    m.flushdb.return_value = True # Add flushdb for clear_all

    # Mock pipeline behavior
    pipeline_mock = MagicMock()

    # Store commands in a list
    _pipeline_commands = []

    def _pipeline_incr(key):
        _pipeline_commands.append(("incr", key))

    def _pipeline_expire(key, time_val):
        _pipeline_commands.append(("expire", key, time_val))

    def _pipeline_delete(key): # New: delete command in pipeline
        _pipeline_commands.append(("delete", key))

    def _pipeline_execute():
        results = []
        for cmd in _pipeline_commands:
            if cmd[0] == "incr":
                results.append(mock_incr(cmd[1]))
            elif cmd[0] == "expire":
                results.append(mock_expire(cmd[1], cmd[2]))
            elif cmd[0] == "delete": # Execute delete from pipeline
                results.append(mock_delete(cmd[1]))
        _pipeline_commands.clear()
        return results

    pipeline_mock.incr.side_effect = _pipeline_incr
    pipeline_mock.expire.side_effect = _pipeline_expire
    pipeline_mock.delete.side_effect = _pipeline_delete # Assign new pipeline delete
    pipeline_mock.execute.side_effect = _pipeline_execute
    m.pipeline.return_value = pipeline_mock

    def reset_store():
        _redis_store.clear()
        _expirations.clear() # Clear expirations too
        _pipeline_commands.clear()
    m.reset_store = reset_store

    return m

@pytest.fixture(scope="function")
def api_client(db_session_factory: sessionmaker, mock_redis: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    mock_redis.reset_store() # Reset Redis mock state for each test function
    
    from main import create_fastapi_app
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
    
    from main import create_fastapi_app
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
