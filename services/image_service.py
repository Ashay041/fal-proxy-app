import httpx          # For downloading images
import os            # For file path operations
import uuid          # For generating unique IDs to prevent filename collisions
from pathlib import Path  # To handle directories

async def download_image(image_url: str) -> bytes:
    """Download image from URL and return bytes"""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        http_response = await http_client.get(image_url)
        http_response.raise_for_status() # raise exception if request failed
        return http_response.content


async def save_image(image_bytes: bytes, upload_directory: str = "./uploads") -> str:
    """
    Save image bytes to disk and return the filename
    
    Returns: filename (not full path). Returns like "filename.jpg"
    """
    # Create uploads directory if it doesn't exist
    Path(upload_directory).mkdir(exist_ok=True)
    
    # Generate unique filename to prevent collisions
    # TODO: handle different image formats (detect .png, .webp, etc)
    unique_filename = f"{uuid.uuid4()}.jpg"

    # Build full file path
    # os.path.join works cross-platform:
    # Linux: "uploads/abc.jpg"
    # Windows: "uploads\abc.jpg"
    full_file_path = os.path.join(upload_directory, unique_filename)
    
    # Write image bytes to file (wb = write binary mode)
    with open(full_file_path, "wb") as image_file:
        image_file.write(image_bytes)
    
    return unique_filename