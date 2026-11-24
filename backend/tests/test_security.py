"""
Security tests: SSRF, non-image, oversized, 404, redirect-to-private.

The sync tests (SSRF validation) run directly.
The async tests mock httpx at the transport level using httpx.MockTransport
to avoid Windows event-loop hangs caused by AsyncMock + httpx.AsyncClient.
"""
import pytest
import httpx
from app.core.security import validate_image_url
from app.services.image_downloader import download_and_validate_image
from app.core.exceptions import PermanentError


# ---- Synchronous SSRF validation tests ----

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


# ---- Async download validation tests using MockTransport ----

@pytest.mark.asyncio
async def test_non_image_url_response():
    """URL that returns text/html instead of an image must raise PermanentError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>Not an image</html>")

    transport = httpx.MockTransport(handler)
    # Monkey-patch the module-level httpx.AsyncClient so download_and_validate_image uses our transport
    original_cls = httpx.AsyncClient
    class _PatchedClient(original_cls):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)
    httpx.AsyncClient = _PatchedClient
    try:
        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/not-an-image.html", allow_local_for_testing=True)
        assert "did not return an image" in exc_info.value.message
    finally:
        httpx.AsyncClient = original_cls

@pytest.mark.asyncio
async def test_oversized_image_response():
    """Image whose content-length exceeds the limit must raise PermanentError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/png", "content-length": str(15 * 1024 * 1024)},
            content=b"A" * 1024,  # Content doesn't matter — header check fires first
        )

    transport = httpx.MockTransport(handler)
    original_cls = httpx.AsyncClient
    class _PatchedClient(original_cls):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)
    httpx.AsyncClient = _PatchedClient
    try:
        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/oversized.png", allow_local_for_testing=True)
        assert "exceeds limit" in exc_info.value.message
    finally:
        httpx.AsyncClient = original_cls

@pytest.mark.asyncio
async def test_unreachable_image_url_404():
    """404 response must raise PermanentError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, headers={}, content=b"")

    transport = httpx.MockTransport(handler)
    original_cls = httpx.AsyncClient
    class _PatchedClient(original_cls):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)
    httpx.AsyncClient = _PatchedClient
    try:
        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/missing.png", allow_local_for_testing=True)
        assert "404" in exc_info.value.message
    finally:
        httpx.AsyncClient = original_cls

@pytest.mark.asyncio
async def test_redirect_to_private_host_is_rejected():
    """A redirect to a private/loopback IP must be caught by SSRF validation."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/internal.png"})

    transport = httpx.MockTransport(handler)
    original_cls = httpx.AsyncClient
    class _PatchedClient(original_cls):
        def __init__(self, **kwargs):
            kwargs["transport"] = transport
            super().__init__(**kwargs)
    httpx.AsyncClient = _PatchedClient
    try:
        with pytest.raises(PermanentError) as exc_info:
            await download_and_validate_image("https://example.com/image.png")
        assert "restricted host" in exc_info.value.message or "private" in exc_info.value.message
    finally:
        httpx.AsyncClient = original_cls
