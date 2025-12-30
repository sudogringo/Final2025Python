"""
Concurrency Tests for Race Condition Fixes

Tests concurrent operations to validate SELECT FOR UPDATE locks
and ensure stock consistency under high concurrency.
"""
import pytest
import concurrent.futures
import threading
from datetime import date
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import Engine

from models.product import ProductModel
from models.order import OrderModel
from models.order_detail import OrderDetailModel
from models.client import ClientModel
from models.bill import BillModel
from models.category import CategoryModel
from services.order_detail_service import OrderDetailService
from schemas.order_detail_schema import OrderDetailSchema
from models.enums import DeliveryMethod, Status, PaymentType


class TestConcurrentStockOperations:
    """Test concurrent operations on stock management"""

    @pytest.mark.skip(reason="SQLite does not fully support pessimistic locking for concurrent tests.")
    def test_concurrent_order_detail_creation_prevents_overselling(self, db_session_factory, engine: Engine):
        """
        Test that 100 concurrent order detail creations don't cause overselling
        """
        session = db_session_factory() # Create a session for seeding
        category = CategoryModel(name="Electronics")
        session.add(category)
        session.commit()

        product = ProductModel(name="Limited Edition Product", price=99.99, stock=10, category_id=category.id_key)
        session.add(product)
        session.commit()

        client = ClientModel(name="Test", lastname="Client", email="test@example.com", telephone="+1234567890")
        session.add(client)
        session.commit()

        bill = BillModel(bill_number="BILL-CONCURRENT-001", total=999.90, client_id=client.id_key, payment_type=PaymentType.CASH)
        session.add(bill)
        session.commit()

        order = OrderModel(date=date(2025, 11, 17), delivery_method=DeliveryMethod.DRIVE_THRU, status=Status.PENDING, client_id=client.id_key, bill_id=bill.id_key)
        session.add(order)
        session.commit()

        ThreadSafeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        successes = []
        failures = []

        def create_order_detail(request_num: int):
            thread_db = ThreadSafeSessionLocal()
            try:
                with thread_db.begin():  # Explicitly begin a transaction
                    service = OrderDetailService(thread_db)
                    schema = OrderDetailSchema(quantity=1, price=product.price, order_id=order.id_key, product_id=product.id_key)
                    service.save(schema)
                    successes.append(request_num)
                    return {"status": "success"}
            except ValueError:
                failures.append(request_num)
                return {"status": "insufficient_stock"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                thread_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(create_order_detail, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_results = [r for r in results if r["status"] == "success"]
        insufficient_stock_results = [r for r in results if r["status"] == "insufficient_stock"]
        error_results = [r for r in results if r["status"] == "error"]

        session.refresh(product) # Refresh the product in the main session
        
        # Original assertions from the test
        assert len(success_results) == 10, f"Expected 10 purchases, got {len(success_results)}"
        assert len(insufficient_stock_results) == 90, f"Expected 90 failures, got {len(insufficient_stock_results)}"
        assert len(error_results) == 0, f"Expected 0 errors, got {len(error_results)}: {error_results}"
        assert product.stock == 0, f"Expected final stock 0, got {product.stock}"

    @pytest.mark.skip(reason="SQLite does not fully support pessimistic locking for concurrent tests.")
    def test_concurrent_order_detail_updates_maintain_stock_consistency(self, db_session_factory, engine: Engine):
        session = db_session_factory()
        category = CategoryModel(name="Electronics")
        session.add(category)
        session.commit()
        product = ProductModel(name="Updatable", price=50.00, stock=100, category_id=category.id_key)
        client = ClientModel(name="Test", lastname="Client", email="update@example.com", telephone="+1234567890")
        bill = BillModel(bill_number="BILL-UPDATE-001", total=50.00, client_id=client.id_key, payment_type=PaymentType.CARD)
        session.add_all([product, client, bill])
        session.commit()
        order = OrderModel(date=date(2025, 11, 17), delivery_method=DeliveryMethod.DRIVE_THRU, status=Status.PENDING, client_id=client.id_key, bill_id=bill.id_key)
        session.add(order)
        session.commit()
        order_detail = OrderDetailModel(quantity=1, price=product.price, order_id=order.id_key, product_id=product.id_key)
        product.stock -= 1
        session.add(order_detail)
        session.commit()

        ThreadSafeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def update_order_detail(new_quantity: int):
            thread_db = ThreadSafeSessionLocal()
            try:
                with thread_db.begin():  # Explicitly begin a transaction
                    service = OrderDetailService(thread_db)
                    schema = OrderDetailSchema(quantity=new_quantity, price=product.price, order_id=order.id_key, product_id=product.id_key)
                    service.update(order_detail.id_key, schema)
                    return {"status": "success"}
            except Exception:
                return {"status": "failure"}
            finally:
                thread_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(update_order_detail, qty) for qty in range(2, 52)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_results = [r for r in results if r["status"] == "success"]
        assert len(success_results) <= 1, "Expected at most 1 successful update"

    @pytest.mark.skip(reason="SQLite does not fully support pessimistic locking for concurrent tests.")
    def test_concurrent_order_detail_deletes_restore_stock_correctly(self, db_session_factory, engine: Engine):
        session = db_session_factory()
        category = CategoryModel(name="Electronics")
        session.add(category)
        session.commit() # Commit category first to get id_key
        initial_stock = 100
        product = ProductModel(name="Deletable", price=25.00, stock=initial_stock - 50, category_id=category.id_key)
        client = ClientModel(name="Test", lastname="Client", email="delete@example.com", telephone="+1234567890")
        bill = BillModel(bill_number="BILL-DELETE-001", total=1250.00, client_id=client.id_key, payment_type=PaymentType.CASH)
        session.add_all([product, client, bill])
        session.commit()
        order = OrderModel(date=date(2025, 11, 17), delivery_method=DeliveryMethod.DRIVE_THRU, status=Status.PENDING, client_id=client.id_key, bill_id=bill.id_key)
        session.add(order)
        session.commit()

        order_detail_ids = []
        for _ in range(10):
            od = OrderDetailModel(quantity=5, price=product.price, order_id=order.id_key, product_id=product.id_key)
            session.add(od)
            session.commit()
            order_detail_ids.append(od.id_key)

        ThreadSafeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def delete_order_detail(od_id: int):
            thread_db = ThreadSafeSessionLocal()
            try:
                with thread_db.begin():  # Explicitly begin a transaction
                    service = OrderDetailService(thread_db)
                    service.delete(od_id)
                    return {"status": "success"}
            except Exception:
                return {"status": "error"}
            finally:
                thread_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(delete_order_detail, od_id) for od_id in order_detail_ids]
            [f.result() for f in concurrent.futures.as_completed(futures)]
        
        session.refresh(product)
        assert product.stock == initial_stock

@pytest.mark.integration
class TestConcurrentCacheOperations:
    """Test concurrent cache operations with distributed locks"""

    def test_concurrent_cache_stampede_prevention(self, db_session_factory):
        """
        Test that cache stampede protection works with concurrent requests
        """
        pytest.skip("Skipping cache stampede test as it requires a real cache service setup.")