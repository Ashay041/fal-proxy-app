import httpx
import os
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type


MAX_IMAGE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB limit for downloads
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit for uploads
DOWNLOAD_CHUNK_SIZE_BYTES = 8192  # 8KB chunks for streaming
DOWNLOAD_TIMEOUT_SECONDS = 30.0
STORAGE_BUCKET_NAME = "fal_images"

# Magic bytes for file type detection (first bytes of the file)
# These are the actual binary signatures that identify the file format
# Link: https://www.ease.ws/forensics/fileCarving/fileSignatures.html
MAGIC_BYTES = {
    "image/jpeg": [
        bytes([0xFF, 0xD8, 0xFF])  # JPEG signature
    ],
    "image/png": [
        bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])  # PNG signature
    ]
}

# Load Supabase credentials
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Retry decorator: Automatically retries 3 times with exponential backoff (1s, 2s, 4s)
# This handles temporary network failures, timeouts, and server errors
# ValueError is excluded from retries because it indicates validation errors (e.g., file too large)
@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def download_image(image_url: str) -> bytes:
    """
    Downloads image with TRUE streaming protection and automatic retry.
    Checks size chunk-by-chunk to prevent memory exhaustion attacks.
    
    Retry behavior:
    - Attempt 1: Immediate
    - Attempt 2: Wait 1 second
    - Attempt 3: Wait 2 seconds
    - Attempt 4: Wait 4 seconds
    - If all fail: raises the last exception
    
    Security considerations:
    - Malicious users could provide URLs to large files
    - Loading entire file into memory could crash the server
    - So we download in chunks and abort if limit exceeded
    
    Args:
        image_url: URL of the image to download
    Returns:
        bytes: Raw image data
    """
    headers = {
        "User-Agent": "FalProxyApp/1.0 (Educational Project; +http://localhost:8000)"
    }
    
    async with httpx.AsyncClient(
        timeout=DOWNLOAD_TIMEOUT_SECONDS, 
        follow_redirects=True, 
        headers=headers
    ) as http_client:
        async with http_client.stream("GET", image_url) as response:
            response.raise_for_status()
            
            # Fast fail: Check Content-Length header if present
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE_BYTES:
                raise ValueError(
                    f"Image too large ({int(content_length)} bytes). "
                    f"Maximum allowed: {MAX_IMAGE_SIZE_BYTES} bytes."
                )
            
            # Safe download: Read in chunks and abort if limit exceeded
            # Why chunked downloading prevents crashes:
            # - Malicious actors can send Content-Length: 1MB but actually stream 10GB
            # - Loading entire file into memory first may cause OOM crash (Out Of Memory)
            # - Chunked approach: check size after each 8KB chunk, abort immediately if exceeded
            # - Memory footprint: max 100MB (our limit) instead of unlimited
            downloaded_data = b""
            async for chunk in response.aiter_bytes(chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
                downloaded_data += chunk
                
                if len(downloaded_data) > MAX_IMAGE_SIZE_BYTES:
                    raise ValueError(
                        f"Download aborted: Image exceeded {MAX_IMAGE_SIZE_BYTES} bytes."
                    )
            
            return downloaded_data


async def save_image(image_bytes: bytes) -> str:
    """
    Uploads image to Supabase Storage and returns a public URL.
    No format validation - fal.ai will validate the image format.
    
    Why we upload to Supabase instead of serving from our server:
    1. fal.ai needs publicly accessible URLs (can't reach localhost)
    2. Supabase provides CDN-backed storage (fast global access)
    
    Args:
        image_bytes: Raw image data to upload
    Returns:
        str: Public URL to the uploaded image   
    """
    # Generate cryptographically random filename to prevent collisions
    unique_filename = f"{uuid.uuid4()}"

    # Upload to cloud storage
    supabase.storage.from_(STORAGE_BUCKET_NAME).upload(
        path=unique_filename,
        file=image_bytes,
        file_options={
            "content-type": "image/jpeg",  # Default content-type
            "upsert": "true"  # Overwrite if UUID collision (extremely rare)
        }
    )

    # Get the permanent public URL
    public_access_url = supabase.storage.from_(STORAGE_BUCKET_NAME).get_public_url(
        unique_filename
    )

    return public_access_url


def validate_image_type_from_magic_bytes(file_content: bytes) -> str:
    """
    Detects the actual image type by reading the file's magic bytes.

    Magic bytes are the binary signature at the start of a file that identify
    its true format. This cannot be faked like MIME types or file extensions.

    Args:
        file_content: The raw bytes of the uploaded file

    Returns:
        str: The detected MIME type (e.g., "image/jpeg", "image/png")

    Raises:
        ValueError: If the file is not a valid JPEG or PNG image
    """
    # Check each supported format's magic bytes
    for mime_type, signatures in MAGIC_BYTES.items():
        for signature in signatures:
            if file_content.startswith(signature):
                return mime_type

    # If no magic bytes match, reject the file
    raise ValueError(
        "Invalid image file. Only JPEG and PNG images are allowed. "
        "The file does not have a valid image signature."
    )


def validate_upload_file_size(file_size: int) -> None:
    """
    Validates that the uploaded file size is within allowed limits.

    Security considerations:
    - Prevents users from uploading extremely large files
    - 10MB limit is reasonable for image uploads
    - Protects storage quota and processing resources

    Args:
        file_size: Size of the file in bytes

    Raises:
        ValueError: If the file size exceeds the limit
    """
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise ValueError(
            f"File size ({size_mb:.2f}MB) exceeds the maximum allowed size of {limit_mb}MB."
        )


