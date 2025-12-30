# Gemini Code Assistant Guide: FastAPI E-commerce API

This document provides a comprehensive overview of the FastAPI E-commerce API project, synthesized from the existing documentation. It is designed to be a quick-start guide for developers and AI assistants to understand the project's architecture, features, and operational procedures.

## 1. Project Overview

This project is an enterprise-grade, production-ready REST API for an e-commerce system. It's built with Python and FastAPI, following a clean, layered architecture. The system is designed for high performance, security, and observability, capable of handling 400+ concurrent users.

**Key characteristics:**
- **Stateless:** The API does not maintain state between requests.
- **Asynchronous:** Built on FastAPI's ASGI foundation for high throughput.
- **Layered Architecture:** Strict separation of concerns.
- **Production-Ready:** Includes features like structured logging, health checks, rate limiting, and robust error handling.

## 2. Tech Stack

- **Framework:** FastAPI 0.104.1
- **Language:** Python 3.11.6
- **Database:** PostgreSQL 13
- **Caching & Rate Limiting:** Redis 7
- **ORM:** SQLAlchemy 2.0.23 (with Alembic for migrations)
- **Data Validation:** Pydantic 2.5.1
- **Server:** Uvicorn 0.24.0 (with 4-8 workers in production)
- **Containerization:** Docker & Docker Compose

## 3. Architecture

The application follows a 4-layer clean architecture pattern to ensure separation of responsibilities and maintainability.

```
+-------------------------------------------------+
|  1. Controllers (HTTP Layer)                    |  <-- FastAPI Routers, Pydantic Schemas
|     - Handles HTTP requests/responses           |
|     - Input validation & serialization          |
+----------------------+--------------------------+
                       |
+----------------------v--------------------------+
|  2. Services (Business Logic Layer)             |  <-- Core business rules, transactions
|     - Orchestrates operations                   |
|     - Implements caching, business validation   |
+----------------------+--------------------------+
                       |
+----------------------v--------------------------+
|  3. Repositories (Data Access Layer)            |  <-- Abstracts data source
|     - Implements CRUD operations                |
|     - Uses SQLAlchemy Session                   |
+----------------------+--------------------------+
                       |
+----------------------v--------------------------+
|  4. Models (Domain Layer)                       |  <-- SQLAlchemy ORM Models
|     - Defines database schema and relationships |
+-------------------------------------------------+
```

### Key Design Patterns
- **Repository Pattern:** Decouples business logic from data access. `BaseRepositoryImpl` provides generic CRUD methods.
- **Service Layer:** Encapsulates business logic, ensuring it's not scattered in controllers.
- **Dependency Injection:** FastAPI's `Depends` system is used to inject database sessions (`get_db`) into controllers and services, ensuring each request gets a fresh session that is closed afterward.
- **Cache-Aside Pattern:** The application first checks Redis for data. If it's a cache miss, it fetches from PostgreSQL and stores the result in Redis for subsequent requests.

## 4. Getting Started (Docker - Recommended)

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <project-folder>
    ```

2.  **Configure Environment:**
    Copy the example environment file and edit if necessary. For local development, the defaults are usually sufficient.
    ```bash
    cp .env.example .env
    ```

3.  **Run with Docker Compose:**
    This command will build the images and start the API, PostgreSQL, and Redis containers.
    ```bash
    docker-compose up --build
    ```

4.  **Verify the API:**
    Check the health of the system.
    ```bash
    curl http://localhost:8000/health_check
    ```
    You should see a `"status": "healthy"` response.

5.  **Access Interactive API Docs:**
    - **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
    - **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 5. Key Business Logic & Features

The API implements critical business rules to ensure data integrity and security.

-   **Stock Management:**
    -   **Pessimistic Locking (`SELECT FOR UPDATE`)** is used when creating an order detail to prevent race conditions and overselling.
    -   Stock is automatically decremented when an item is added to an order.
    -   Stock is automatically restored if an order detail is deleted or an order is canceled.

-   **Price Validation:**
    -   When adding a product to an order, the price submitted in the request is validated against the actual price in the database. This prevents price manipulation from the client-side.

-   **Data Integrity:**
    -   **Foreign Key constraints** are enforced at the database level.
    -   The application logic validates the existence of related entities (e.g., `client_id`, `product_id`) before creating new records, providing clear `404 Not Found` errors.
    -   Products or categories with associated sales cannot be deleted, preventing orphaned records and preserving sales history (returns `409 Conflict`).

-   **Caching:**
    -   **Products:** Cached for 5 minutes.
    -   **Categories:** Cached for 1 hour (as they change infrequently).
    -   Cache is automatically invalidated on `POST`, `PUT`, and `DELETE` operations.
    -   Responses include an `X-Cache-Hit` header.

-   **Rate Limiting:**
    -   **Global:** 100 requests per 60 seconds per IP address.
    -   **Endpoint-Specific:** More restrictive limits on sensitive endpoints like order creation or user registration.
    -   Exceeding the limit returns an `HTTP 429 Too Many Requests` error with a `Retry-After` header.

## 6. API Endpoint Summary

| Resource | Endpoints | Caching | Key Business Logic |
| :--- | :--- | :--- | :--- |
| `/clients` | CRUD | No | Unique email validation. |
| `/products` | CRUD | 5 mins | Cannot delete if sales exist. |
| `/categories`| CRUD | 1 hour | Cannot delete if products exist. |
| `/orders` | CRUD | No | FK validation, status management. |
| `/order_details`| CRUD | No | **Stock and price validation.** |
| `/bills` | CRUD | No | Unique bill number. |
| `/reviews` | CRUD | No | Rating validation [0.0, 5.0]. |
| `/addresses` | CRUD | No | Linked to a client. |
| `/health_check`| GET | No | Monitors DB, Redis, and connection pool. |

## 7. Testing

The project has a comprehensive test suite with **>80% code coverage**.

-   **Location:** `tests/` directory.
-   **Technology:** `pytest`.
-   **Database:** Uses an in-memory SQLite database for test isolation.

### How to Run Tests

1.  **Install development dependencies:**
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Run all tests:**
    ```bash
    pytest tests/ -v
    ```

3.  **Run tests with coverage report:**
    ```bash
    pytest tests/ --cov=. --cov-report=html
    # Open htmlcov/index.html to view the report
    ```

### Load Testing
The project includes a `load_test.py` script for `locust`. It is configured to simulate 400 concurrent users to validate performance targets.

```bash
# Install locust (included in requirements-dev.txt)
# Run the test
locust -f load_test.py --host=http://localhost:8000 --users 400 --spawn-rate 50 --headless
```

## 8. Deployment & Performance

The application is designed for production and high performance.

-   **Deployment:** Use `docker-compose.production.yaml` which configures multiple Uvicorn workers and optimized settings. An Nginx reverse proxy is recommended for load balancing and SSL termination.
-   **Connection Pooling:** Uses SQLAlchemy's `QueuePool` to efficiently manage database connections. The pool is configured for 4 workers, supporting up to 600 total connections to PostgreSQL.
-   **Database Indexes:** All foreign keys and frequently queried columns are indexed to ensure fast lookups.
-   **Observability:**
    -   **Structured Logging:** Logs can be formatted as JSON for easy parsing.
    -   **Request ID:** A `RequestIDMiddleware` injects a unique ID into every request, which is included in all related log entries for easy tracing.
    -   **Health Check:** The `/health_check` endpoint provides detailed status of the database (with latency), Redis, and the DB connection pool utilization.
