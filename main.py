from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from fastapi.staticfiles import StaticFiles

from services.image_service import download_image, save_image
from services.fal_service import kontext_blocking, kontext_nonblocking, kontext_blocking_mock, kontext_nonblocking_mock


app = FastAPI(title="fal proxy app")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Defining what data we expect using pydantic
class ImageRequest(BaseModel):
    image_url: HttpUrl  # Validates it's actually a URL
    prompt: str


@app.get("/")
async def root():
    return {"message": "fal proxy app is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/kontext")
async def kontext_proxy(request: ImageRequest):
    """Complete proxy - synchronous fal.ai call"""
    # Download user's input image from their URL
    user_input_image_bytes = await download_image(str(request.image_url))
    
    # Save to our storage and get the filename
    stored_input_filename = await save_image(user_input_image_bytes)
    proxy_input_image_url = f"http://localhost:8000/uploads/{stored_input_filename}"
    
    #TODO: remove this, it is mock function for testing
    fal_api_response = kontext_blocking_mock(
        image_url=proxy_input_image_url,
        prompt=request.prompt
    )

    # Call fal.ai with our proxy URL
    # fal_api_response = kontext_blocking(
    #     image_url=proxy_input_image_url,
    #     prompt=request.prompt
    # )
    #TODO: remove this
    print(fal_api_response)
    
    # Download and save fal.ai's generated output images
    proxy_response_images = []
    for generated_image in fal_api_response.get("images", []):
        # Download each generated image from fal.ai
        generated_image_bytes = await download_image(generated_image["url"])
        
        # Save to our storage
        generated_image_filename = await save_image(generated_image_bytes)
        
        # Build our proxy URL for the generated image
        proxy_generated_image_url = f"http://localhost:8000/uploads/{generated_image_filename}"
        
        proxy_response_images.append({
            "url": proxy_generated_image_url,
            "width": generated_image.get("width"),
            "height": generated_image.get("height")
        })
    
    return {
        "images": proxy_response_images,
        "prompt": fal_api_response.get("prompt")
    }


@app.post("/kontext-async")
async def kontext_proxy_async(request: ImageRequest):
    """Complete proxy - async fal.ai call"""
    # Download user's input image from their URL
    user_input_image_bytes = await download_image(str(request.image_url))
    
    # Save to our storage and get the filename
    stored_input_filename = await save_image(user_input_image_bytes)
    proxy_input_image_url = f"http://localhost:8000/uploads/{stored_input_filename}"
    
    #TODO: remove this, it is mock function for testing
    fal_api_response = await kontext_nonblocking_mock(
        image_url=proxy_input_image_url,
        prompt=request.prompt
    )
    
    #TODO: uncomment this when fal.ai is ready
    # Call fal.ai with async version
    # fal_api_response = await kontext_nonblocking(
    #     image_url=proxy_input_image_url,
    #     prompt=request.prompt
    # )
    
    # Download and save fal.ai's generated output images
    proxy_response_images = []
    for generated_image in fal_api_response.get("images", []):
        # Download each generated image from fal.ai
        generated_image_bytes = await download_image(generated_image["url"])
        
        # Save to our storage
        generated_image_filename = await save_image(generated_image_bytes)
        
        # Build our proxy URL for the generated image
        proxy_generated_image_url = f"http://localhost:8000/uploads/{generated_image_filename}"
        
        proxy_response_images.append({
            "url": proxy_generated_image_url,
            "width": generated_image.get("width"),
            "height": generated_image.get("height")
        })
    
    return {
        "images": proxy_response_images,
        "prompt": fal_api_response.get("prompt")
    }
