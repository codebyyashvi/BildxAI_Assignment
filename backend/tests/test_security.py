import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.core.security import validate_image_url
from app.services.image_downloader import download_and_validate_image
from app.core.exceptions import PermanentError

def test_ssrf_rejects_localhost():
    with pytest.raises(PermanentError) as exc_info:
        validate_image_url("http://localhost:8000/image.png")
    assert "restricted host" in exc_info.value.message or "private" in exc_info.value.message

def test_ssrf_rejects_loopback_ip():
    with pytest.raises(PermanentError) as exc_info:
        validate_image_url("http://127.0.0.1/malicious.png")
    assert "restricted host" in exc_info.value.message or "private" in exc_info.value.message

def test_ssrf_rejects_cloud_metadata():
    with pytest.raises(PermanentError) as exc_info:
        validate_image_url("http://169.254.169.254/latest/meta-data/")
    assert "restricted host" in exc_info.value.message or "private" in exc_info.value.message

def test_ssrf_rejects_non_http_scheme():
    with pytest.raises(PermanentError) as exc_info:
        validate_image_url("file:///etc/passwd")
    assert "Unsupported URL scheme" in exc_info.value.message

@pytest.mark.asyncio
async def test_non_image_url_response():
    resp = httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>Not an image</html>")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp

        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/not-an-image.html", allow_local_for_testing=True)
        assert "did not return an image" in exc_info.value.message

@pytest.mark.asyncio
async def test_oversized_image_response():
    resp = httpx.Response(
        200,
        headers={"content-type": "image/png", "content-length": str(15 * 1024 * 1024)},
        content=b"A" * (11 * 1024 * 1024)
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp

        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/oversized.png", allow_local_for_testing=True)
        assert "exceeds limit" in exc_info.value.message

@pytest.mark.asyncio
async def test_unreachable_image_url_404():
    resp = httpx.Response(404, headers={}, content=b"")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resp

        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/missing.png", allow_local_for_testing=True)
        assert "404" in exc_info.value.message
