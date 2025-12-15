import httpx
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv

# Load Supabase credentials
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def validate_is_jpeg_image(raw_file_bytes: bytes) -> None:
    """
    Inspects the file header (Magic Bytes) to ensure the data is a JPEG.
    Raises ValueError if the bytes do not match the JPEG signature.
    """
    # The first 2 bytes of every JPEG file are always FF D8 (hex)
    jpeg_magic_signature = b'\xff\xd8'

    if not raw_file_bytes.startswith(jpeg_magic_signature):
        raise ValueError(
            "Invalid image format. Strictly JPEG images are allowed for now."
        )


async def download_image(image_url: str) -> bytes:
    """
    Downloads image with TRUE streaming protection.
    It checks size chunk-by-chunk to prevent memory overflows/crashes.
    """
    # Safety Limit: 100MB
    MAX_IMAGE_SIZE = 100 * 1024 * 1024 
    
    headers = {
        "User-Agent": "FalProxyApp/1.0 (Educational Project; +http://localhost:8000)"
    }
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as http_client:
        async with http_client.stream("GET", image_url) as response:
            response.raise_for_status()
            
            # 1. Fast Fail: Check header if it exists
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE:
                raise ValueError(f"Image too large ({int(content_length)} bytes). Limit is {MAX_IMAGE_SIZE} bytes.")
            
            # 2. Safe Download: Read in chunks (e.g., 8KB at a time)
            downloaded_data = b""
            async for chunk in response.aiter_bytes(chunk_size=8192):
                downloaded_data += chunk
                
                # STOP immediately if we exceed the limit
                if len(downloaded_data) > MAX_IMAGE_SIZE:
                    raise ValueError(f"Download aborted: Image exceeded {MAX_IMAGE_SIZE} bytes limit.")
            
            return downloaded_data


async def save_image(image_bytes: bytes) -> str:
    """
    Validates, uploads, and returns a public URL for the image.
    """
    # 1. Enforce strict type checking before doing any work
    validate_is_jpeg_image(image_bytes)

    # 2. Generate a random filename
    unique_filename = f"{uuid.uuid4()}.jpg"
    storage_bucket_name = "fal_images"

    # 3. Upload to Supabase Storage
    # upsert=True overwrites if a file collision theoretically happens
    supabase.storage.from_(storage_bucket_name).upload(
        path=unique_filename,
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"}
    )

    # 4. Generate and return the public access URL
    public_access_url = supabase.storage.from_(storage_bucket_name).get_public_url(unique_filename)
    
    return public_access_url