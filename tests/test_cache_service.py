import pytest
from unittest.mock import patch, MagicMock
from services.cache_service import generate_unique_request_key, retrieve_cached_response, store_response_in_cache


def test_cache_key_includes_model_path():
    """
    Verify cache keys differ for different model paths.
    Why: Different models produce different outputs; must avoid returning cached results from wrong model.
    """
    key1 = generate_unique_request_key("url", "prompt", "fal-ai/flux-pro/kontext")
    key2 = generate_unique_request_key("url", "prompt", "fal-ai/flux-kontext/dev")
    
    assert key1 != key2


def test_cache_key_same_for_identical_inputs():
    """
    Verify identical inputs produce the same cache key.
    Why: Deterministic key generation is required for cache lookups to work.
    """
    key1 = generate_unique_request_key("url", "prompt", "model")
    key2 = generate_unique_request_key("url", "prompt", "model")
    
    assert key1 == key2


def test_retrieve_returns_none_when_redis_disabled():
    """
    Verify cache retrieval returns None when Redis is unavailable.
    Why: Service should continue working even if Redis is not configured.
    """
    with patch("services.cache_service.redis_client", None):
        result = retrieve_cached_response("url", "prompt", "model")
        assert result is None


def test_store_handles_redis_disabled():
    """
    Verify cache storage doesn't crash when Redis is unavailable.
    Why: Caching is optional; service must remain resilient to infrastructure issues.
    """
    with patch("services.cache_service.redis_client", None):
        result = store_response_in_cache("url", "prompt", "model", {"data": "test"})
        assert result is None