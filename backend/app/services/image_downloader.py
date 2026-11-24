import io
import httpx
from urllib.parse import urljoin
from PIL import Image
from app.core.config import settings
from app.core.security import validate_image_url
from app.core.exceptions import PermanentError, TemporaryError

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF", "BMP"}

async def download_and_validate_image(url: str, allow_local_for_testing: bool = False) -> bytes:
    """
    Downloads remote product image safely with strict timeouts, size limits, and format verification.
    """
    validate_image_url(url, allow_local_for_testing=allow_local_for_testing)

    headers = {
        "User-Agent": "BildxAI-AdGen-Bot/1.0 (+https://bildx.ai)",
        "Accept": "image/webp,image/png,image/jpeg,image/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=False) as client:
            try:
                current_url = url
                response = None
                for _ in range(4):
                    response = await client.get(current_url, headers=headers)
                    if response.status_code not in (301, 302, 303, 307, 308):
                        break
                    location = response.headers.get("location")
                    if not location:
                        raise PermanentError("Image server returned a redirect without a destination.")
                    current_url = urljoin(current_url, location)
                    # Validate every redirect target, not just the initial URL.
                    validate_image_url(
                        current_url,
                        allow_local_for_testing=allow_local_for_testing,
                    )
                else:
                    raise PermanentError("Image URL exceeded the maximum of 4 redirects.")
            except httpx.TimeoutException as e:
                raise TemporaryError(f"Image download timed out after {settings.DOWNLOAD_TIMEOUT_SECONDS}s: {str(e)}")
            except (httpx.ConnectError, httpx.NetworkError) as e:
                raise TemporaryError(f"Temporary network error downloading image from '{url}': {str(e)}")
            except Exception as e:
                raise PermanentError(f"Failed to initiate download for image: {str(e)}")

            if response.status_code == 404:
                raise PermanentError(f"Image not found (404) at URL '{url}'.")
            elif response.status_code >= 500:
                raise TemporaryError(f"Remote server returned temporary error ({response.status_code}) for '{url}'.")
            elif response.status_code >= 400:
                raise PermanentError(f"Remote server rejected image request with status {response.status_code}.")

            content_type = response.headers.get("content-type", "").lower()
            # Some servers may send binary/octet-stream, we will verify with PIL anyway
            if content_type and not any(ct in content_type for ct in ("image/", "application/octet-stream")):
                raise PermanentError(f"URL did not return an image. Received Content-Type: '{content_type}'.")

            # Check declared content-length
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > settings.MAX_IMAGE_SIZE_BYTES:
                raise PermanentError(f"Image size exceeds limit of {settings.MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB.")

            image_bytes = response.content
            if len(image_bytes) > settings.MAX_IMAGE_SIZE_BYTES:
                raise PermanentError(f"Image size ({len(image_bytes)} bytes) exceeds limit of {settings.MAX_IMAGE_SIZE_BYTES} bytes.")

            if len(image_bytes) == 0:
                raise PermanentError("Downloaded image file is empty.")

            # Validate that the bytes actually form a valid recognized image
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    img.verify()
                    fmt = img.format
                    if fmt not in ALLOWED_IMAGE_FORMATS:
                        raise PermanentError(f"Unsupported image format '{fmt}'. Must be one of: {ALLOWED_IMAGE_FORMATS}")
            except PermanentError:
                raise
            except Exception as e:
                raise PermanentError(f"File at '{url}' is corrupt or not a valid image: {str(e)}")

            return image_bytes

    except (PermanentError, TemporaryError):
        raise
    except Exception as e:
        raise PermanentError(f"Unexpected error during image download: {str(e)}")
