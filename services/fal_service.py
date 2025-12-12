import fal_client # fal client for fal.ai
import os # for environment variables

# there are 2 ways to call fal.ai or the client
# 1. using fal_client.subscribe (blocking call)
# 2. Async submit_async (Non-blocking)

# 1. using fal_client.subscribe blocking call
def kontext_blocking(image_url: str, prompt: str) -> dict:
    """
    Synchronous version - blocks until complete
    Good for: simple implementation, <100 concurrent users
    fastapi has around 50 threads only so this is not a good option for production
    Limited to ~50 simultaneous users
    """
    fal_api_response = fal_client.subscribe(
        "fal-ai/flux-pro/kontext",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
        },
        with_logs=False,    #set to True to get logs and helpful to show progress bar
    )
    return fal_api_response

# 2. Async submit_async (Non-blocking)
async def kontext_nonblocking(image_url: str, prompt: str) -> dict:
    """
    Async version - non-blocking
    Good for: production scale, 1000+ concurrent users
    """
    async_job_handler = await fal_client.submit_async(
        "fal-ai/flux-pro/kontext",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
        },
    )
    
    fal_api_response = await async_job_handler.get()
    return fal_api_response

    # Mock function for testing without API key
def kontext_blocking_mock(image_url: str, prompt: str) -> dict:
    """
    Mock version - returns fake response instantly
    Use this when you don't have FAL_KEY
    """
    return {
        "images": [
            {
                "url": "https://fal.media/files/tiger/7dSJbIU_Ni-0Zp9eaLsvR_fe56916811d84ac69c6ffc0d32dca151.jpg",
                "width": 1024,
                "height": 1024,
                "content_type": "image/jpeg"  # For testing purposes
            }
        ],
        "timings": {},
        "seed": 123456,
        "has_nsfw_concepts": [False],
        "prompt": prompt
    }

async def kontext_nonblocking_mock(image_url: str, prompt: str) -> dict:
    """
    Async mock version - returns fake response matching real fal.ai structure
    Simulates async behavior with a tiny delay
    """
    # simulate processing delay
    import asyncio
    await asyncio.sleep(5)
    
    return {
        "images": [
            {
                "url": "https://wallpapers-clan.com/wp-content/uploads/2023/02/minecraft-blocktopia-wallpaper.jpg",
                "width": 800,
                "height": 800,
                "content_type": "image/jpeg"
            }
        ],
        "timings": {},
        "seed": 111111,  # Different seed to distinguish from sync
        "has_nsfw_concepts": [False],
        "prompt": prompt
    }