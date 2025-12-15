from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import os

# Internal services
from services.image_service import download_image, save_image
from services.fal_service import kontext_nonblocking

# Database setup
from services.database import engine, Base
from services import models

# Cache imports
from services.cache_service import retrieve_cached_response, store_response_in_cache

# Load environment variables
load_dotenv()

FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise ValueError("FAL_KEY not found in .env file! App cannot start.")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="fal proxy app")


class ImageRequest(BaseModel):
    """
    Inherits from Pydantic's BaseModel
    Without this:
    - You'd manually validate every field
    - No type hints may cause more bugs
    - API users wouldn't know what fields to send
    """
    image_url: HttpUrl
    prompt: str

# Instead of hardcoding endpoint paths in multiple places, we define them once here.
FAL_ENDPOINT_CONFIG = {
    "kontext": "fal-ai/flux-pro/kontext",
    "kontext-max": "fal-ai/flux-pro/kontext/max", 
    "kontext-dev": "fal-ai/flux-kontext/dev"
}

# This function contains ALL the repeated logic from your original endpoints.
# Now we write it ONCE and reuse it everywhere.
async def process_kontext_request(request: ImageRequest, fal_model_path: str) -> dict:
    """
    Generic handler for ALL kontext endpoints with granular error handling.
    
    Each critical step has its own try-catch so we can pinpoint failures.
    """
    
    # Check cache (doesn't need try-catch since it gracefully returns None on failure)
    cached_result = retrieve_cached_response(str(request.image_url), request.prompt, fal_model_path)
    if cached_result:
        return cached_result
    
    # STEP 1: Download user's input image
    try:
        user_source_image_bytes = await download_image(str(request.image_url))
    except ValueError as e:
        # User error: invalid URL, wrong format, too large
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download input image: {str(e)}"
        )
    except Exception as e:
        # Network/server error after retries
        print(f"Input image download error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to download input image after multiple attempts. Please check the URL and try again."
        )
    
    # STEP 2: Upload input image to Supabase
    try:
        public_input_image_url = await save_image(user_source_image_bytes)
    except ValueError as e:
        # Image validation failed
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Supabase upload failed
        print(f"Supabase upload error (input): {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload input image to storage. Please try again."
        )
    
    # STEP 3: Call fal.ai API
    try:
        fal_api_response = await kontext_nonblocking(
            image_url=public_input_image_url,
            prompt=request.prompt,
            model_path=fal_model_path
        )
    except Exception as e:
        # fal.ai API failed after retries
        print(f"fal.ai API error: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again in a few moments."
        )
    
    # STEP 4: Download and upload generated images
    try:
        processed_response_images = []
        for remote_image_data in fal_api_response.get("images", []):
            remote_image_url = remote_image_data["url"]
            
            # Download generated image from fal.ai
            generated_asset_bytes = await download_image(remote_image_url)
            
            # Upload to our Supabase storage
            public_generated_url = await save_image(generated_asset_bytes)  
            
            processed_response_images.append({
                "url": public_generated_url,
                "width": remote_image_data.get("width"),
                "height": remote_image_data.get("height")
            })
    except Exception as e:
        # Failed to process generated images
        print(f"Generated image processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process generated images. The AI completed but we couldn't save the results."
        )
    
    # Build response
    response_data = {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }

    # Save to cache (doesn't need try-catch since cache failures shouldn't break the request)
    store_response_in_cache(str(request.image_url), request.prompt, fal_model_path, response_data)

    return response_data


@app.get("/")
async def root():
    return {"message": "fal proxy app is running, go to /docs# for API documentation"}

@app.post("/kontext")
async def kontext_endpoint(request: ImageRequest):
    """Standard kontext endpoint"""
    return await process_kontext_request(
        request=request,
        fal_model_path=FAL_ENDPOINT_CONFIG["kontext"]
    )

@app.post("/kontext/max")
async def kontext_max_endpoint(request: ImageRequest):
    """Max quality kontext endpoint"""
    return await process_kontext_request(
        request=request,
        fal_model_path=FAL_ENDPOINT_CONFIG["kontext-max"]
    )

@app.post("/kontext/dev")
async def kontext_dev_endpoint(request: ImageRequest):
    """Development/experimental kontext endpoint"""
    return await process_kontext_request(
        request=request,
        fal_model_path=FAL_ENDPOINT_CONFIG["kontext-dev"]
    )