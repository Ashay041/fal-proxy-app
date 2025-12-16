from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import os
from typing import Optional, Literal

# Internal services
from services.image_service import download_image, save_image
from services.fal_service import kontext_nonblocking

# Database setup
from services.database import engine, Base
from services import models

# Cache imports
from services.cache_service import (
    retrieve_cached_response,
    store_response_in_cache,
    retrieve_cached_response_for_upload,
    store_response_in_cache_for_upload
)

import base64
from services.image_service import validate_upload_file_size, validate_image_type_from_magic_bytes


# Load environment variables
load_dotenv()

FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise ValueError("FAL_KEY not found in .env file! App cannot start.")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="fal proxy app")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class ImageRequest(BaseModel):
    """
    Inherits from Pydantic's BaseModel
    Without this:
    - You'd manually validate every field
    - No type hints may cause more bugs
    - API users wouldn't know what fields to send
    """
    # Image input: either URL or base64 data (not both)
    image_url: Optional[HttpUrl] = None
    image_data: Optional[str] = None  # base64 encoded image
    prompt: str

    # ALL THE OPTIONAL PARAMETERS
    seed: Optional[int] = None
    guidance_scale: Optional[float] = None
    sync_mode: Optional[bool] = None
    num_images: Optional[int] = None
    output_format: Optional[Literal["jpeg", "png"]] = None
    enhance_prompt: Optional[bool] = None
    safety_tolerance: Optional[Literal["1", "2", "3", "4", "5", "6"]] = None
    aspect_ratio: Optional[Literal["21:9", "16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16", "9:21"]] = None
    num_inference_steps: Optional[int] = None
    enable_safety_checker: Optional[bool] = None
    acceleration: Optional[Literal["none", "regular", "high"]] = None
    resolution_mode: Optional[Literal["auto", "match_input", "1:1", "16:9", "21:9", "3:2", "2:3", "4:5", "5:4", "3:4", "4:3", "9:16", "9:21"]] = None

# Instead of hardcoding endpoint paths in multiple places, define them once here.
FAL_ENDPOINT_CONFIG = {
    "kontext": "fal-ai/flux-pro/kontext",
    "kontext-max": "fal-ai/flux-pro/kontext/max",
    "kontext-dev": "fal-ai/flux-kontext/dev"
}


# This function contains ALL the repeated logic from your original endpoints.
# Now we write it ONCE and reuse it everywhere.
async def process_kontext_request(request: ImageRequest, fal_model_path: str) -> dict:
    """
    Generic handler for ALL kontext endpoints.

    Supports two input methods:
    1. image_url: Download from URL
    2. image_data: Decode base64 from file upload

    Both follow the same flow after getting the image bytes.
    """
    # Validate: exactly one input method
    if not request.image_url and not request.image_data:
        raise HTTPException(
            status_code=400,
            detail="Please provide either image_url or image_data"
        )
    if request.image_url and request.image_data:
        raise HTTPException(
            status_code=400,
            detail="Please provide only one: image_url OR image_data, not both"
        )
    
    # Check cache for both URLs and uploads
    cached_result = None
    if request.image_url:
        cached_result = retrieve_cached_response(str(request.image_url), request.prompt, fal_model_path)
    elif request.image_data:
        cached_result = retrieve_cached_response_for_upload(request.image_data, request.prompt, fal_model_path)
    if cached_result:
        return cached_result

    # STEP 1: Get image bytes (different source, same result)
    try:
        if request.image_url:
            # From URL: download it
            user_source_image_bytes = await download_image(str(request.image_url))
        else:
            # From upload: decode base64
            user_source_image_bytes = base64.b64decode(request.image_data)
            # Validate the uploaded file size
            validate_upload_file_size(len(user_source_image_bytes))

        # Validate image type for both URL and upload
        validate_image_type_from_magic_bytes(user_source_image_bytes)
    except ValueError as e:
        # User error: invalid URL, wrong format, too large
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process input image: {str(e)}"
        )
    except Exception as e:
        # Network/server error after retries (for URLs)
        print(f"Input image processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process input image. Please check the input and try again."
        )

    # STEP 2: Upload input image to Supabase (SAME for both)
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
            model_path=fal_model_path,
            seed=request.seed,
            guidance_scale=request.guidance_scale,
            sync_mode=request.sync_mode,
            num_images=request.num_images,
            output_format=request.output_format,
            enhance_prompt=request.enhance_prompt,
            safety_tolerance=request.safety_tolerance,
            aspect_ratio=request.aspect_ratio,
            num_inference_steps=request.num_inference_steps,
            enable_safety_checker=request.enable_safety_checker,
            acceleration=request.acceleration,
            resolution_mode=request.resolution_mode
        )
    except Exception as e:
        # fal.ai API failed after retries
        print(f"fal.ai API error: {e}")
        raise HTTPException(
            status_code=503,
            detail="fal.ai had a problem"
        )

    # STEP 4: Download and upload generated images (SAME for both)
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
            detail="Failed to process generated images. The fal.ai completed but we couldn't save the results."
        )

    # Build response
    response_data = {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }

    # Step 5: Save to cache (for both URL and upload requests)
    if request.image_url:
        store_response_in_cache(str(request.image_url), request.prompt, fal_model_path, response_data)
    elif request.image_data:
        store_response_in_cache_for_upload(request.image_data, request.prompt, fal_model_path, response_data)

    return response_data


@app.get("/")
async def root():
    """Serve the frontend UI"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    """API health check endpoint"""
    return {"message": "fal proxy app is running, go to /docs# for API documentation"}


@app.post("/kontext")
async def kontext_endpoint(request: ImageRequest):
    """Standard kontext endpoint that accepts image_url or image_data with prompt"""
    return await process_kontext_request(request, FAL_ENDPOINT_CONFIG["kontext"])


@app.post("/kontext/max")
async def kontext_max_endpoint(request: ImageRequest):
    """Max quality kontext endpoint that accepts image_url or image_data with prompt"""
    return await process_kontext_request(request, FAL_ENDPOINT_CONFIG["kontext-max"])


@app.post("/kontext/dev")
async def kontext_dev_endpoint(request: ImageRequest):
    """Dev kontext endpoint that accepts image_url or image_data with prompt"""
    return await process_kontext_request(request, FAL_ENDPOINT_CONFIG["kontext-dev"])