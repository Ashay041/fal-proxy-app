import redis
import json
import hashlib
import os

CACHE_TTL_SECONDS = 3600  # 1 hour default expiration for cached responses
REDIS_URL = os.getenv("REDIS_URL")

try:
    redis_client = redis.Redis.from_url(
        REDIS_URL, 
        decode_responses=True  # Return strings instead of bytes
    )
    redis_client.ping()
    print("Redis connection successful")
except Exception as e:
    print(f"Redis connection failed: {e}")
    print("Cache will be disabled - all requests will hit fal.ai API")
    redis_client = None


def generate_unique_request_key(image_url: str, prompt: str, model_path: str) -> str:
    """
    Creates a cache key from request inputs including the model path.
    
    Why we include model_path:
    - Same image + prompt on different models produce different results
    - /kontext vs /kontext/max should have separate cache entries
    
    Why SHA256 hashing - Same inputs always produce same key
    Key structure: kontext_cache:<hash>
    """
    input_signature = f"{image_url}::{prompt}::{model_path}"
    hashed_signature = hashlib.sha256(input_signature.encode()).hexdigest()
    cache_key = f"kontext_cache:{hashed_signature}"
    return cache_key


def retrieve_cached_response(image_url: str, prompt: str, model_path: str):
    """
    Attempts to retrieve cached API response from Redis for a specific model.
    
    Returns:
        dict: Cached response if found
        None: If cache miss or Redis unavailable
    
    Graceful degradation:
    - If Redis is down, returns None (app continues working)
    - Cache failures don't crash the application
    """
    if redis_client is None:
        return None
        
    try:
        cache_key = generate_unique_request_key(image_url, prompt, model_path)
        cached_json_string = redis_client.get(cache_key)
        
        if cached_json_string:
            print(f"Cache HIT: {cache_key}")
            return json.loads(cached_json_string)
        else:
            print(f"Cache MISS: {cache_key}")
            
    except Exception as read_error:
        print(f"Cache read error: {read_error}")
    
    return None


def store_response_in_cache(
    image_url: str, 
    prompt: str,
    model_path: str,
    response_data: dict, 
    expiration_seconds: int = CACHE_TTL_SECONDS
):
    """
    Saves API response to Redis with TTL for a specific model.
    
    Why we use expiration:
    - Images on fal.ai might expire after some time
    - Prevents serving stale results indefinitely
    - Automatically manages cache size (old entries get deleted)
    
    Args:
        model_path: Which fal.ai model was used (for cache separation)
        expiration_seconds: How long to keep in cache (default: 1 hour)
    """
    if redis_client is None:
        return

    try:
        cache_key = generate_unique_request_key(image_url, prompt, model_path)
        json_string = json.dumps(response_data)
        
        redis_client.setex(cache_key, expiration_seconds, json_string)
        print(f"Cache SAVE: {cache_key} (TTL: {expiration_seconds}s)")
        
    except Exception as e:
        print(f"Cache write error: {e}")