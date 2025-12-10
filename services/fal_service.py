import fal_client # fal client for fal.ai
import os # for environment variables
from dotenv import load_dotenv # load environment variables from .env file

# Load API key from environment
load_dotenv()

# there are 2 ways to call fal.ai or the client
# 1. using fal_client.subscribe (blocking call)
# 2. Async submit_async (Non-blocking)

# 1. using fal_client.subscribe blocking call
def call_kontext_sync(image_url: str, prompt: str) -> dict:
    """
    Synchronous: Blocks until fal.ai returns result
    FastAPI runs this in a thread pool
    """
    result = fal_client.subscribe(
        "fal-ai/flux-pro/kontext",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
        },
        with_logs=False,
    )
    return result

# 2. Async submit_async (Non-blocking)

