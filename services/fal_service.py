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
