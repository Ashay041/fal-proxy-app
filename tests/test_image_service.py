import pytest
from unittest.mock import patch
from services.image_service import validate_is_jpeg_image, save_image, download_image

def test_validate_jpeg_works_correctly():
    """
    Ensures that files with valid JPEG magic bytes are accepted.
    This prevents false positives where valid images might be rejected.
    """
    # Given: A byte sequence starting with standard JPEG signatures (\xff\xd8...)
    valid_jpeg_signature = b'\xff\xd8\xff\xe0' 
    
    # When: We run the validation function
    # Then: It should execute successfully without raising an exception
    validate_is_jpeg_image(valid_jpeg_signature)

def test_validate_jpeg_rejects_png():
    """
    Makes sure that non-JPEG files (like PNGs) are strictly rejected.
    We enforce this to maintain consistency in our storage bucket.
    """
    # Given: A byte sequence with PNG magic bytes
    invalid_png_signature = b'\x89PNG'
    
    # When: We attempt to validate the non-JPEG data
    # Then: It must raise a ValueError immediately
    with pytest.raises(ValueError):
        validate_is_jpeg_image(invalid_png_signature)

@pytest.mark.asyncio
async def test_save_image_mocked():
    """
    Verifies that the save_image function correctly calls the Supabase API
    and returns the public URL, without actually uploading files to the cloud.
    """
    # Given: A mocked Supabase client that returns a fixed URL
    with patch("services.image_service.supabase") as mock_db:
        mock_db.storage.from_().get_public_url.return_value = "https://fake.com/img.jpg"

        # And: Valid image bytes to pass the pre-upload validation check
        valid_jpeg_data = b'\xff\xd8\xff\xe0'

        # When: The function attempts to save the image
        result_url = await save_image(valid_jpeg_data)

        # Then: It should return the URL provided by our mock
        assert result_url == "https://fake.com/img.jpg"

@pytest.mark.asyncio
async def test_download_image(httpx_mock):
    """
    Verifies that the downloader correctly retrieves bytes from a URL.
    Uses httpx_mock to avoid making real network requests during tests.
    """
    # Given: A mocked HTTP response containing specific image data
    fake_image_bytes = b"fake-data-from-internet"
    httpx_mock.add_response(url="https://test.com/img.jpg", content=fake_image_bytes)
    
    # When: We request to download that specific URL
    downloaded_bytes = await download_image("https://test.com/img.jpg")
    
    # Then: The returned data must match exactly what the server sent
    assert downloaded_bytes == fake_image_bytes