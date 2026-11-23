import io
import pytest
import pytest_asyncio
from PIL import Image
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    settings.ENVIRONMENT = "test"
    settings.AI_PROVIDER = "fake"
    settings.FAKE_PROVIDER_DELAY_SECONDS = 0.05
    settings.MAX_CONCURRENT_GENERATIONS = 2
    settings.MAX_QUEUE_SIZE = 5
    settings.MAX_RETRIES = 2
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generates valid 300x300 PNG image bytes in memory."""
    img = Image.new("RGBA", (300, 300), color=(50, 120, 220, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
