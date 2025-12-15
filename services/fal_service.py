import fal_client
from tenacity import retry, stop_after_attempt, wait_exponential

# Parameter sets for each endpoint type
KONTEXT_PARAMS = {
    "seed", "guidance_scale", "sync_mode", "num_images", 
    "output_format", "enhance_prompt", "safety_tolerance", "aspect_ratio"
}

KONTEXT_DEV_PARAMS = {
    "seed", "guidance_scale", "sync_mode", "num_images",
    "output_format", "enhance_prompt", "num_inference_steps",
    "enable_safety_checker", "acceleration", "resolution_mode"
}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
async def kontext_nonblocking(image_url: str, prompt: str, model_path: str, **kwargs) -> dict:
    """
    There are 2 ways to call fal.ai or the client - 
    1. using fal_client.subscribe (blocking call)
    2. Async submit_async (Non-blocking)
        
    Why async is better than sync for this use case:
    - Handles 1000+ concurrent users without FastAPI thread exhaustion

    Call fal.ai API with automatic retry on failures.
    Retries 3 times if the API call fails (network issues, API down, etc.)
    
    Args:
        image_url: Publicly accessible URL to the input image
        prompt: Text description of desired edits
        model_path: Which fal.ai model to invoke (e.g. "fal-ai/flux-pro/kontext")
        **kwargs: Optional parameters (filtered based on endpoint)
    
    Returns:
        dict: API response containing generated images and metadata
    """
    arguments = {
        "prompt": prompt,
        "image_url": image_url,
    }
    
    # Filter parameters based on endpoint
    if "dev" in model_path:
        allowed_params = KONTEXT_DEV_PARAMS
    else:
        allowed_params = KONTEXT_PARAMS
    
    # Only add parameters that are allowed for this endpoint
    for key, value in kwargs.items():
        if value is not None and key in allowed_params:
            arguments[key] = value
    
    async_job_handler = await fal_client.submit_async(model_path, arguments=arguments)
    fal_api_response = await async_job_handler.get()
    return fal_api_response