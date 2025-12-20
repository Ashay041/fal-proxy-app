import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os

# Use SQLite in-memory database for tests
# This prevents database connection errors in CI/CD environments
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from main import app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI app.
    This allows testing without running the actual server.
    """
    return TestClient(app)


@pytest.mark.parametrize("endpoint", ["/kontext", "/kontext/max", "/kontext/dev"])
def test_rate_limiting_enforced(client, endpoint):
    """
    Verify that rate limiting is enforced on kontext endpoints.

    Tests that:
    - First 5 requests succeed
    - 6th request is rate limited (429)

    Why: Prevents bot abuse and protects FAL API budget
    """
    # Mock the entire processing function to avoid actual API calls
    with patch("main.process_kontext_request", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = {
            "images": [{"url": "https://fake-url.com/image.jpg"}],
            "prompt": "test prompt"
        }

        # Valid test payload
        payload = {
            "image_url": "https://picsum.photos/200",
            "prompt": "test prompt"
        }

        success_count = 0
        rate_limited_count = 0

        # Send 7 requests to test the 5/minute limit
        for i in range(7):
            response = client.post(endpoint, json=payload)

            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1

        # Verify rate limiting behavior
        assert success_count == 5, f"Expected 5 successful requests, got {success_count}"
        assert rate_limited_count == 2, f"Expected 2 rate limited requests, got {rate_limited_count}"


def test_rate_limit_error_message(client):
    """
    Verify that rate limit error messages are clear and informative.

    Why: Users should understand why their request was rejected
    """
    with patch("main.process_kontext_request", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = {
            "images": [{"url": "https://fake-url.com/image.jpg"}],
            "prompt": "test prompt"
        }

        payload = {
            "image_url": "https://picsum.photos/200",
            "prompt": "test prompt"
        }

        # Make 6 requests to trigger rate limit
        for i in range(6):
            response = client.post("/kontext", json=payload)

        # Check the error message format
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.text or "rate limit" in response.text.lower()


def test_health_endpoint_not_rate_limited(client):
    """
    Verify that health check endpoint is not rate limited.

    Why: Health checks should always be accessible for monitoring
    """
    # Send many requests to health endpoint
    for i in range(20):
        response = client.get("/health")
        assert response.status_code == 200, f"Health endpoint should not be rate limited"


def test_root_endpoint_not_rate_limited(client):
    """
    Verify that root endpoint is not rate limited.

    Why: Frontend UI should always be accessible
    """
    # Send many requests to root endpoint
    for i in range(20):
        response = client.get("/")
        assert response.status_code == 200, f"Root endpoint should not be rate limited"
