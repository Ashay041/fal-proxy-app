import redis
import json
import hashlib
import os

# Get the single URL string
REDIS_URL = os.getenv("REDIS_URL")

try:
    # We add decode_responses=True so we get Strings back, not Bytes
    redis_client = redis.Redis.from_url(
        REDIS_URL, 
        decode_responses=True
    )
    
    redis_client.ping()
    print("System: Successfully connected to Redis (via URL)")
except Exception as e:
    print(f"System Warning: Redis connection failed. Error: {e}")
    redis_client = None

def generate_unique_request_key(image_url: str, prompt: str) -> str:
    """
    Generates a deterministic SHA256 hash based on the input parameters.
    This ensures the same input always produces the same cache key.
    """
    # Create a unique string signature from inputs
    input_signature = f"{image_url}::{prompt}"
    
    # Hash the signature to create a safe, fixed-length key
    hashed_signature = hashlib.sha256(input_signature.encode()).hexdigest()
    
    # Return with a prefix to avoid collisions with other potential keys
    return f"kontext_cache:{hashed_signature}"

def retrieve_cached_response(image_url: str, prompt: str):
    """
    Attempts to retrieve a previous result from Redis.
    Returns the JSON object if found, otherwise None.
    """
    if redis_client is None:
        return None
        
    try:
        cache_key = generate_unique_request_key(image_url, prompt)
        cached_json_string = redis_client.get(cache_key)
        
        if cached_json_string:
            print(f"Cache: Hit found for key {cache_key[:10]}...")
            return json.loads(cached_json_string)
            
    except Exception as read_error:
        print(f"Cache Error: Failed to read from Redis. Details: {read_error}")
    
    return None

def store_response_in_cache(image_url: str, prompt: str, response_data: dict, expiration_seconds=3600):
    """
    Saves the API response to Redis with an expiration time (TTL).
    Default TTL is 1 hour (3600 seconds).
    """
    if redis_client is None:
        return

    try:
        cache_key = generate_unique_request_key(image_url, prompt)
        json_string_to_store = json.dumps(response_data)
        
        # Save to Redis with Expiration (setex)
        redis_client.setex(cache_key, expiration_seconds, json_string_to_store)
        print(f"Cache: Successfully saved result for key {cache_key[:10]}...")
        
    except Exception as write_error:
        print(f"Cache Error: Failed to write to Redis. Details: {write_error}")