from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from services.image_service import download_image, save_image
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="fal proxy app")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Defining what data we expect using pydantic
class ImageRequest(BaseModel):
    image_url: HttpUrl  # Validates it's actually a URL
    prompt: str

@app.get("/")
async def root():
    return {"message": "fal proxy app is running"}

@app.post("/test-endpoint")
async def test_endpoint(request: ImageRequest):
    return {
        "received_image_url": str(request.image_url),
        "received_prompt": request.prompt,
        "status": "this is just echoing back your input"
    }

@app.post("/test-save")
async def test_save(request: ImageRequest):
    # Download
    image_bytes = await download_image(str(request.image_url))
    
    # Save
    filename = await save_image(image_bytes)
    
    return {
        "original_url": str(request.image_url),
        "saved_filename": filename,
        "size_bytes": len(image_bytes)
    }

@app.post("/kontext-sync")
async def kontext_sync_endpoint(request: ImageRequest):
    """Uses synchronous fal client"""
    result = call_kontext_sync(
        image_url=str(request.image_url),
        prompt=request.prompt
    )
    return result
    
        