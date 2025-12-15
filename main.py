from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import os

# Internal services
from services.image_service import download_image, save_image
from services.fal_service import kontext_blocking, kontext_nonblocking

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
    image_url: HttpUrl
    prompt: str

@app.get("/")
async def root():
    return {"message": "fal proxy app is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/kontext-sync")
async def kontext_sync_proxy(request: ImageRequest):
    # 1. CHECK CACHE
    cached_result = retrieve_cached_response(str(request.image_url), request.prompt)
    if cached_result:
        return cached_result
    
    # 2. DO WORK (Cache Miss)
    user_source_image_bytes = await download_image(str(request.image_url))
    public_input_image_url = await save_image(user_source_image_bytes)
    
    fal_api_response = kontext_blocking(
        image_url=public_input_image_url,
        prompt=request.prompt
    )
    
    processed_response_images = []
    for remote_image_data in fal_api_response.get("images", []):
        remote_image_url = remote_image_data["url"]
        generated_asset_bytes = await download_image(remote_image_url)
        public_generated_url = await save_image(generated_asset_bytes)
        
        processed_response_images.append({
            "url": public_generated_url,
            "width": remote_image_data.get("width"),
            "height": remote_image_data.get("height")
        })
    
    response_data = {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }

    # 3. SAVE TO CACHE
    store_response_in_cache(str(request.image_url), request.prompt, response_data)

    return response_data

@app.post("/kontext-async")
async def kontext_proxy_async(request: ImageRequest):
    # 1. CHECK CACHE
    cached_result = retrieve_cached_response(str(request.image_url), request.prompt)
    if cached_result:
        return cached_result

    # 2. DO WORK
    user_source_image_bytes = await download_image(str(request.image_url))
    public_input_image_url = await save_image(user_source_image_bytes)
    
    fal_api_response = await kontext_nonblocking(
        image_url=public_input_image_url,
        prompt=request.prompt
    )
    
    processed_response_images = []
    for remote_image_data in fal_api_response.get("images", []):
        remote_image_url = remote_image_data["url"]
        generated_asset_bytes = await download_image(remote_image_url)
        public_generated_url = await save_image(generated_asset_bytes)
        
        processed_response_images.append({
            "url": public_generated_url,
            "width": remote_image_data.get("width"),
            "height": remote_image_data.get("height")
        })
    
    response_data = {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }

    # 3. SAVE TO CACHE
    store_response_in_cache(str(request.image_url), request.prompt, response_data)

    return response_data