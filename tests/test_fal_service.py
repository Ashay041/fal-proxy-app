import pytest
from unittest.mock import AsyncMock, patch
from services.fal_service import kontext_nonblocking


@pytest.mark.asyncio
async def test_kontext_filters_dev_params():
    """
    Verify kontext endpoint filters out dev-only parameters like num_inference_steps.
    Why: Different endpoints accept different params; sending wrong ones causes API errors.
    """
    with patch("services.fal_service.fal_client") as mock_fal:
        mock_handler = AsyncMock()
        mock_handler.get = AsyncMock(return_value={"images": []})
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        
        await kontext_nonblocking(
            image_url="https://example.com/img.jpg",
            prompt="test",
            model_path="fal-ai/flux-pro/kontext",
            num_inference_steps=50,  # dev-only param
            safety_tolerance="3"  # kontext param
        )
        
        call_args = mock_fal.submit_async.call_args[1]["arguments"]
        assert "safety_tolerance" in call_args
        assert "num_inference_steps" not in call_args


@pytest.mark.asyncio
async def test_kontext_dev_filters_kontext_params():
    """
    Verify kontext/dev endpoint filters out kontext-only parameters like safety_tolerance.
    Why: Dev endpoint accepts different params than standard kontext endpoint.
    """
    with patch("services.fal_service.fal_client") as mock_fal:
        mock_handler = AsyncMock()
        mock_handler.get = AsyncMock(return_value={"images": []})
        mock_fal.submit_async = AsyncMock(return_value=mock_handler)
        
        await kontext_nonblocking(
            image_url="https://example.com/img.jpg",
            prompt="test",
            model_path="fal-ai/flux-kontext/dev",
            safety_tolerance="3",  # kontext param
            num_inference_steps=50  # dev param
        )
        
        call_args = mock_fal.submit_async.call_args[1]["arguments"]
        assert "num_inference_steps" in call_args
        assert "safety_tolerance" not in call_args