import httpx          # For downloading images
import os            # For file path operations
import uuid          # For generating unique IDs to prevent filename collisions
from pathlib import Path  # To handle directories

async def download_image(url: str) -> bytes:
    """Download image from URL and return bytes"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status() # raise exception if request failed
        return response.content


async def save_image(image_bytes: bytes, upload_dir: str = "./uploads") -> str:
    """
    Save image bytes to disk and return the filepath
    
    Returns: filename (not full path) like "abc123.jpg"
    """
    # Create uploads directory if it doesn't exist
    Path(upload_dir).mkdir(exist_ok=True)
    
    # Generate unique filename
    # TODO: handle different image formats
    filename = f"{uuid.uuid4()}.jpg"

    # os.path.join(
    # Linux: "uploads/abc.jpg"
    # Windows: "uploads\abc.jpg"
    filepath = os.path.join(upload_dir, filename)
    
    # Write bytes to file, wb as it is image
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    
    return filename