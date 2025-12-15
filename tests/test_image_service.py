import pytest
from services.image_service import download_image, save_image
import os
from pathlib import Path


@pytest.mark.asyncio
async def test_save_image_creates_file(tmp_path):
    """Test that save_image creates a file with the correct content"""
    # Given: Some fake image bytes
    fake_image_data = b"fake image bytes for testing"
    
    # When: We save the image
    filename = await save_image(fake_image_data, upload_directory=str(tmp_path))
    
    # Then: File should exist and contain the data
    assert filename.endswith('.jpg')
    file_path = tmp_path / filename
    assert file_path.exists()
    assert file_path.read_bytes() == fake_image_data


@pytest.mark.asyncio
async def test_save_image_generates_unique_filenames(tmp_path):
    """Test that multiple saves generate different filenames"""
    # Given: Same image data
    fake_image_data = b"same data"
    
    # When: We save twice
    filename1 = await save_image(fake_image_data, upload_directory=str(tmp_path))
    filename2 = await save_image(fake_image_data, upload_directory=str(tmp_path))
    
    # Then: Filenames should be different (UUID ensures uniqueness)
    assert filename1 != filename2


@pytest.mark.asyncio
async def test_save_image_creates_directory_if_missing(tmp_path):
    """Test that save_image creates upload directory if it doesn't exist"""
    # Given: A directory that doesn't exist yet
    new_dir = tmp_path / "new_uploads"
    assert not new_dir.exists()
    
    # When: We save an image
    fake_image_data = b"test"
    filename = await save_image(fake_image_data, upload_directory=str(new_dir))
    
    # Then: Directory should be created
    assert new_dir.exists()
    assert (new_dir / filename).exists()


@pytest.mark.asyncio
async def test_download_image_success(httpx_mock):
    """Test successful image download"""
    # Given: A URL and mock response
    test_url = "https://example.com/image.jpg"
    fake_image_bytes = b"fake downloaded image"
    httpx_mock.add_response(url=test_url, content=fake_image_bytes)
    
    # When: We download the image
    result = await download_image(test_url)
    
    # Then: Should return the image bytes
    assert result == fake_image_bytes


@pytest.mark.asyncio
async def test_download_image_follows_redirects(httpx_mock):
    """Test that download_image follows HTTP redirects"""
    # Given: A URL that redirects
    redirect_url = "https://example.com/redirect"
    final_url = "https://example.com/final.jpg"
    fake_image_bytes = b"final image"
    
    httpx_mock.add_response(
        url=redirect_url, 
        status_code=302,
        headers={"Location": final_url}
    )
    httpx_mock.add_response(url=final_url, content=fake_image_bytes)
    
    # When: We download from redirect URL
    result = await download_image(redirect_url)
    
    # Then: Should get image from final destination
    assert result == fake_image_bytes


@pytest.mark.asyncio
async def test_download_image_handles_404(httpx_mock):
    """Test that download_image raises error on 404"""
    # Given: A URL that returns 404
    test_url = "https://example.com/missing.jpg"
    httpx_mock.add_response(url=test_url, status_code=404)
    
    # When/Then: Should raise HTTPStatusError
    with pytest.raises(Exception):  # httpx.HTTPStatusError
        await download_image(test_url)