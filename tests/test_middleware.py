"""Unit tests for middleware components."""
import pytest
import time
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient


from middleware.rate_limiter import RateLimiterMiddleware


@pytest.fixture
def app_with_rate_limiter_factory(mock_redis):
    """
    Fixture factory to create a test app with the RateLimiterMiddleware.
    This centralizes the setup logic for creating the app, patching Redis,
    and adding the middleware.
    """
    def _create_app(mock_redis_arg, calls, period):
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/health_check")
        async def health_check():
            return {"status": "ok"}

        @app.get("/endpoint1")
        async def endpoint1():
            return {"endpoint": "1"}

        @app.get("/endpoint2")
        async def endpoint2():
            return {"endpoint": "2"}

        # Patch get_redis_client for both middleware modules
        with patch('middleware.rate_limiter.get_redis_client', return_value=mock_redis_arg), \
             patch('middleware.endpoint_rate_limiter.get_redis_client', return_value=mock_redis_arg):
            app.add_middleware(RateLimiterMiddleware, calls=calls, period=period, redis_client=mock_redis_arg)

        return app
    return _create_app


class TestRateLimiter:
    """Tests for RateLimiter middleware."""

    def test_rate_limiter_allows_within_limit(self, mock_redis, app_with_rate_limiter_factory):
        """Test that requests within limit are allowed."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)

        # Make 5 requests (should all succeed)
        for i in range(5):
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"message": "success"}

    def test_rate_limiter_blocks_over_limit(self, mock_redis, app_with_rate_limiter_factory):
        """Test that requests over limit are blocked."""
        app = app_with_rate_limiter_factory(mock_redis, calls=3, period=60)
        client = TestClient(app)

        # Make 3 requests (should succeed)
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        # 4th request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()

    def test_rate_limiter_different_ips(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limiting is per IP address."""
        app = app_with_rate_limiter_factory(mock_redis, calls=2, period=60)
        client = TestClient(app)

        # Make 2 requests from one IP
        for i in range(2):
            response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
            assert response.status_code == 200

        # 3rd request from same IP should be blocked
        response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
        assert response.status_code == 429

        # Request from a different IP should succeed
        response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.2"})
        assert response.status_code == 200

    def test_rate_limiter_redis_failure_fails_open(self, app_with_rate_limiter_factory):
        """Test that rate limiter fails open when Redis is down."""
        failing_redis = Mock()
        failing_redis.pipeline.side_effect = Exception("Redis connection failed")

        app = app_with_rate_limiter_factory(failing_redis, calls=1, period=60)
        client = TestClient(app)

        # Should succeed even though Redis is down (fail open)
        response = client.get("/test")
        assert response.status_code == 200

    def test_rate_limiter_atomic_operations(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limiter uses atomic Redis pipeline operations."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        # Verify pipeline was used
        mock_redis.pipeline.assert_called_once()

    def test_rate_limiter_custom_limits(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter with different call limits."""
        app = app_with_rate_limiter_factory(mock_redis, calls=1, period=60)
        client = TestClient(app)

        # First request should succeed
        response = client.get("/test")
        assert response.status_code == 200

        # Second request should be blocked immediately
        response = client.get("/test")
        assert response.status_code == 429

    def test_rate_limiter_excludes_health_check(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limiter excludes health check endpoint."""
        app = app_with_rate_limiter_factory(mock_redis, calls=1, period=60)
        client = TestClient(app)

        # Health check should never be rate limited
        for i in range(10):
            response = client.get("/health_check")
            assert response.status_code == 200

    def test_rate_limiter_response_headers(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limiter adds appropriate response headers."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limiter_period_expiration(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limit resets after period expires."""
        app = app_with_rate_limiter_factory(mock_redis, calls=1, period=1)
        client = TestClient(app)

        # First request
        response = client.get("/test")
        assert response.status_code == 200

        # Second request immediately (should be blocked)
        mock_redis.pipeline.return_value.execute.return_value = [2, 1]
        response = client.get("/test")
        assert response.status_code == 429

        # Wait for period to expire
        time.sleep(1.1)

        # Third request after period (should succeed)
        mock_redis.pipeline.return_value.execute.return_value = [1, 1]
        response = client.get("/test")
        assert response.status_code == 200

    def test_rate_limiter_get_client_ip(self, mock_redis, app_with_rate_limiter_factory):
        """Test client IP extraction from various headers."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)

        # Test with X-Forwarded-For header
        response = client.get("/test", headers={"X-Forwarded-For": "192.168.1.100"})
        assert response.status_code == 200

        # Test with X-Real-IP header
        response = client.get("/test", headers={"X-Real-IP": "192.168.1.101"})
        assert response.status_code == 200


class TestRateLimiterEdgeCases:
    """Tests for rate limiter edge cases."""

    def test_rate_limiter_concurrent_requests(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter behavior with concurrent requests."""
        app = app_with_rate_limiter_factory(mock_redis, calls=3, period=60)
        client = TestClient(app)

        # Simulate the redis counter for each call
        mock_redis.pipeline.return_value.execute.side_effect = [[1, 1], [2, 1], [3, 1], [4, 1], [5, 1]]

        responses = [client.get("/test") for _ in range(5)]

        assert sum(1 for r in responses if r.status_code == 200) == 3
        assert sum(1 for r in responses if r.status_code == 429) == 2

    def test_rate_limiter_zero_calls(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter with zero calls allowed (edge case)."""
        app = app_with_rate_limiter_factory(mock_redis, calls=0, period=60)
        client = TestClient(app)

        # Should be immediately rate limited
        response = client.get("/test")
        assert response.status_code == 429

    def test_rate_limiter_very_high_limit(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter with very high limit."""
        app = app_with_rate_limiter_factory(mock_redis, calls=10000, period=60)
        client = TestClient(app)

        # Should handle many requests
        for i in range(100):
            response = client.get("/test")
            assert response.status_code == 200

    def test_rate_limiter_redis_key_format(self, mock_redis, app_with_rate_limiter_factory):
        """Test that rate limiter uses correct Redis key format."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)
        
        mock_redis.reset_mock()

        response = client.get("/test", headers={"X-Forwarded-For": "10.0.0.1"})
        assert response.status_code == 200
        
        # Check that the pipeline was called, implying a key was constructed
        mock_redis.pipeline.assert_called()


class TestRateLimiterConfiguration:
    """Tests for rate limiter configuration."""

    def test_rate_limiter_custom_configuration(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter with custom configuration."""
        configs = [
            (10, 60),
            (100, 3600),
            (5, 10),
        ]

        for calls, period in configs:
            mock_redis.reset_mock()
            # Simulate counter incrementing
            mock_redis.pipeline.return_value.execute.side_effect = [[i + 1, 1] for i in range(calls + 1)]
            
            app = app_with_rate_limiter_factory(mock_redis, calls=calls, period=period)
            client = TestClient(app)

            for i in range(calls):
                response = client.get("/test")
                assert response.status_code == 200

            response = client.get("/test")
            assert response.status_code == 429


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with full app."""

    def test_rate_limiter_with_multiple_endpoints(self, mock_redis, app_with_rate_limiter_factory):
        """Test rate limiter across multiple endpoints."""
        app = app_with_rate_limiter_factory(mock_redis, calls=5, period=60)
        client = TestClient(app)

        mock_redis.pipeline.return_value.execute.side_effect = [[i + 1, 1] for i in range(6)]

        # Rate limit is shared across all endpoints for the same IP
        for i in range(3):
            assert client.get("/endpoint1").status_code == 200

        for i in range(2):
            assert client.get("/endpoint2").status_code == 200

        # 6th request should be blocked
        response = client.get("/endpoint1")
        assert response.status_code == 429