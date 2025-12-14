import httpx
import os
import uuid
from supabase import create_client, Client

# Load Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Fail fast if credentials are missing
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def validate_is_jpeg_image(raw_file_bytes: bytes) -> None:
    """
    Checks the file header to ensure the data is a JPEG.

    Why: We are currently restricting the application to JPEGs only to simplify
    the processing pipeline. This prevents issues with unsupported formats
    like PNG or WEBP/GIF.

    Raises:
        ValueError: If the bytes do not match the JPEG signature.
    """
    # The first 2 bytes of every JPEG file are always FF D8 (hex)
    jpeg_magic_signature = b'\xff\xd8'

    if not raw_file_bytes.startswith(jpeg_magic_signature):
        raise ValueError(
            "Invalid image format. Strictly JPEG images are allowed for now."
        )


async def download_image(image_url: str) -> bytes:
    """
    Downloads raw image bytes from a given URL.
    Includes headers to prevent 403 Forbidden errors from sites like Wikimedia.
    """
    # Define headers to mimic a real browser/valid client
    headers = {
        "User-Agent": "FalProxyApp/1.0 (Educational Project; +http://localhost:8000)"
    }
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as http_client:
        http_response = await http_client.get(image_url)
        http_response.raise_for_status()
        return http_response.content

async def save_image(image_bytes: bytes) -> str:
    """
    Validates, uploads, and returns a public URL for the image.
    """
    # 1. Enforce strict type checking before doing any work
    validate_is_jpeg_image(image_bytes)

    # 2. Generate a random filename
    # We can safely hardcode .jpg now because we validated the content
    unique_filename = f"{uuid.uuid4()}.jpg"
    storage_bucket_name = "fal_images"

    # 3. Upload to Supabase Storage
    # We set upsert=True to overwrite if a file collision theoretically happens
    supabase.storage.from_(storage_bucket_name).upload(
        path=unique_filename,
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"}
    )

    # 4. Generate and return the public access URL
    public_access_url = supabase.storage.from_(storage_bucket_name).get_public_url(unique_filename)
    
    return public_access_url