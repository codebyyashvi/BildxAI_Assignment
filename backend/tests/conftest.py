import sys
import asyncio
import io
import os
import platform

# Windows event loop fix - must happen before any async imports
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
import pytest_asyncio
from PIL import Image

# Set test env BEFORE importing app to avoid loading .env overrides
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AI_PROVIDER", "fake")
os.environ.setdefault("FAKE_PROVIDER_DELAY_SECONDS", "0.05")

from app.core.config import settings  # noqa: E402

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    settings.ENVIRONMENT = "test"
    settings.AI_PROVIDER = "fake"
    settings.FAKE_PROVIDER_DELAY_SECONDS = 0.05
    settings.MAX_CONCURRENT_GENERATIONS = 3
    settings.MAX_QUEUE_SIZE = 10
    settings.MAX_RETRIES = 2
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

@pytest.fixture
def sync_client():
    """Synchronous TestClient — works reliably on Windows without event loop issues."""
    from starlette.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        yield client

@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generates valid 300x300 PNG image bytes in memory."""
    img = Image.new("RGBA", (300, 300), color=(50, 120, 220, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
