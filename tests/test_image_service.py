import pytest
from unittest.mock import patch, AsyncMock
from services.image_service import save_image, download_image


@pytest.mark.asyncio
async def test_save_image_uploads_to_supabase():
    """
    Verify that save_image uploads to Supabase and returns a public URL.
    Why: Ensures images are stored correctly and accessible to clients.
    """
    with patch("services.image_service.supabase") as mock_supabase:
        mock_supabase.storage.from_().get_public_url.return_value = "https://fake-url.com/image"
        
        image_data = b"fake-image-data"
        result = await save_image(image_data)
        
        assert result == "https://fake-url.com/image"
        mock_supabase.storage.from_().upload.assert_called_once()


@pytest.mark.asyncio
async def test_download_image_success(httpx_mock):
    """
    Verify that download_image retrieves image data from a URL.
    Why: Proxy service downloads images from FAL.AI temporary URLs before storing.
    """
    fake_bytes = b"image-content"
    httpx_mock.add_response(url="https://example.com/image.jpg", content=fake_bytes)
    
    result = await download_image("https://example.com/image.jpg")
    
    assert result == fake_bytes


@pytest.mark.asyncio
async def test_download_image_rejects_large_files(httpx_mock):
    """
    Verify that images exceeding 100MB are rejected by checking Content-Length.
    Why: Prevents memory exhaustion, bandwidth costs, and timeouts from huge files.
    """
    httpx_mock.add_response(
        url="https://example.com/huge.jpg",
        headers={"Content-Length": str(200 * 1024 * 1024)}  # 200MB
    )
    
    with pytest.raises(ValueError, match="Image too large"):
        await download_image("https://example.com/huge.jpg")