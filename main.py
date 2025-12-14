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

# Load environment variables (FAL_KEY, SUPABASE_URL, etc.)
load_dotenv()

# Verify API key exists before starting
FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise ValueError("FAL_KEY not found in .env file! App cannot start.")

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="fal proxy app")

# NOTE: We no longer mount "/uploads" because images are hosted on Supabase Storage.

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
    """
    Synchronous Proxy Endpoint:
    1. Downloads image from User.
    2. Uploads to Supabase to get a Public URL.
    3. Sends Public URL + Prompt to Fal.ai.
    4. Downloads Fal.ai result -> Uploads to Supabase -> Returns Public URL to User.
    """
    # 1. Acquire the raw bytes from the user's provided URL
    user_source_image_bytes = await download_image(str(request.image_url))
    
    # 2. Upload to our cloud storage (Supabase) and get a URL that Fal.ai can access
    public_input_image_url = await save_image(user_source_image_bytes)
    
    # 3. Trigger the Fal.ai inference using our public URL
    fal_api_response = kontext_blocking(
        image_url=public_input_image_url,
        prompt=request.prompt
    )
    
    # 4. Process the results
    processed_response_images = []
    
    for remote_image_data in fal_api_response.get("images", []):
        remote_image_url = remote_image_data["url"]
        
        # Download the generated asset
        generated_asset_bytes = await download_image(remote_image_url)
        
        # Persist to our storage (Supabase)
        public_generated_url = await save_image(generated_asset_bytes)
        
        processed_response_images.append({
            "url": public_generated_url,
            "width": remote_image_data.get("width"),
            "height": remote_image_data.get("height")
        })
    
    return {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }

@app.post("/kontext-async")
async def kontext_proxy_async(request: ImageRequest):
    """
    Asynchronous Proxy Endpoint.
    Same logic as /kontext-sync but uses non-blocking Fal.ai submission.
    """
    user_source_image_bytes = await download_image(str(request.image_url))
    public_input_image_url = await save_image(user_source_image_bytes)
    
    # Use the async/non-blocking version of the service
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
    
    return {
        "images": processed_response_images,
        "prompt": fal_api_response.get("prompt")
    }