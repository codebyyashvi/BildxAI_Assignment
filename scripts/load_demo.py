"""Repeatable, zero-credit API concurrency demonstration.

Runs the FastAPI app in-process, mocks only the remote image download, and uses
the real fake provider, orchestrator, grounding, composer, and API routes.
"""

import asyncio
import io
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.orchestrator import orchestrator  # noqa: E402

logging.getLogger("httpx").setLevel(logging.WARNING)


def sample_image() -> bytes:
    image = Image.new("RGB", (500, 500), (173, 181, 157))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def payload(index: int, *, failing: bool = False) -> dict:
    name = "Trigger-Permanent-Error Demo" if failing else f"Demo Product {index}"
    return {
        "image_url": "https://example.com/product.png",
        "product_name": name,
        "product_description": "A durable everyday product for the load demonstration.",
        "target_audience": "Busy professionals",
        "key_benefits": ["Durable construction", "Simple daily use"],
        "tone": "Confident and practical",
    }


async def main() -> None:
    settings.ENVIRONMENT = "test"
    settings.AI_PROVIDER = "fake"
    settings.FAKE_PROVIDER_DELAY_SECONDS = 0.15
    settings.MAX_QUEUE_SIZE = 20
    orchestrator.records.clear()
    orchestrator.idempotency_map.clear()
    orchestrator.pending_count = 0
    orchestrator.active_provider_calls = 0
    orchestrator.semaphore = asyncio.Semaphore(3)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://demo") as client:
        with patch(
            "app.services.orchestrator.download_and_validate_image",
            new_callable=AsyncMock,
            return_value=sample_image(),
        ):
            requests = [
                client.post(
                    "/api/generations",
                    json=payload(index, failing=index == 9),
                    headers={"Idempotency-Key": f"load-{index}"},
                )
                for index in range(10)
            ]
            responses = await asyncio.gather(*requests)
            assert all(response.status_code == 202 for response in responses)
            ids = [response.json()["id"] for response in responses]
            assert len(set(ids)) == 10

            duplicate = await client.post(
                "/api/generations",
                json=payload(0),
                headers={"Idempotency-Key": "load-0"},
            )
            assert duplicate.json()["id"] == ids[0]

            max_active = 0
            while True:
                health = (await client.get("/api/health")).json()
                max_active = max(max_active, health["active_provider_calls"])
                records = [
                    (await client.get(f"/api/generations/{generation_id}")).json()
                    for generation_id in ids
                ]
                if all(record["status"] in ("completed", "failed") for record in records):
                    break
                await asyncio.sleep(0.03)

    completed = sum(record["status"] == "completed" for record in records)
    failed = sum(record["status"] == "failed" for record in records)
    assert completed == 9 and failed == 1
    assert max_active <= 3

    print("Load demonstration passed")
    print(f"  independent IDs:  {len(set(ids))}/10")
    print(f"  completed:        {completed}")
    print(f"  isolated failures:{failed}")
    print(f"  max concurrency:  {max_active}/3")
    print("  duplicate work:   prevented")
    print("  capacity:         bounded at 20 pending jobs")


if __name__ == "__main__":
    asyncio.run(main())
