import asyncio
import io
import pytest
import pytest_asyncio
from PIL import Image
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.services.orchestrator import orchestrator

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
    for task in list(orchestrator._tasks):
        task.cancel()
    if orchestrator._tasks:
        await asyncio.gather(*orchestrator._tasks, return_exceptions=True)
    orchestrator.records.clear()
    orchestrator.idempotency_map.clear()
    orchestrator.pending_count = 0
    orchestrator.active_provider_calls = 0
    orchestrator.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GENERATIONS)
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
