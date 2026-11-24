import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from app.services.orchestrator import orchestrator
from app.schemas.generation import GenerationStatus
from app.core.config import settings

@pytest.mark.asyncio
async def test_full_ad_generation_flow(async_client, sample_image_bytes):
    with patch("app.services.orchestrator.download_and_validate_image", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = sample_image_bytes
        payload = {
            "image_url": "https://bildx.ai/samples/assets/roam-front.webp",
            "product_name": "ROAM Lock 750",
            "product_description": "A 750 ml insulated steel tumbler with a locking sip lid.",
            "target_audience": "Commuters and hikers",
            "key_benefits": ["Up to 12 hours cold", "Carry loop", "Locking lid"],
            "tone": "Adventurous and practical",
            "idempotency_key": "test-flow-key-1"
        }

        # 1. Enqueue generation
        response = await async_client.post("/api/generations", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        gen_id = data["id"]
        assert data["status"] in ("pending", "processing")

        # 2. Poll until completed
        max_attempts = 40
        completed = False
        for _ in range(max_attempts):
            poll_resp = await async_client.get(f"/api/generations/{gen_id}")
            assert poll_resp.status_code == 200
            poll_data = poll_resp.json()
            if poll_data["status"] == GenerationStatus.COMPLETED.value:
                completed = True
                assert poll_data["creative_output"] is not None
                assert "headline" in poll_data["creative_output"]
                assert "supporting_text" in poll_data["creative_output"]
                assert "cta" in poll_data["creative_output"]
                assert poll_data["image_url"] is not None
                break
            elif poll_data["status"] == GenerationStatus.FAILED.value:
                pytest.fail(f"Generation failed prematurely: {poll_data.get('error_message')}")
            await asyncio.sleep(0.05)

        assert completed, "Generation did not reach COMPLETED state within allotted time"

        # 3. Download generated image
        img_resp = await async_client.get(f"/api/generations/{gen_id}/image")
        assert img_resp.status_code == 200
        assert img_resp.headers["content-type"] == "image/png"
        assert len(img_resp.content) > 0

@pytest.mark.asyncio
async def test_api_validation_error(async_client):
    # Missing required fields
    bad_payload = {
        "image_url": "https://example.com/item.png",
        "product_name": ""
    }
    response = await async_client.post("/api/generations", json=bad_payload)
    assert response.status_code == 422 # FastAPI validation failure

@pytest.mark.asyncio
async def test_api_samples_endpoint(async_client):
    response = await async_client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) >= 1
    assert "product_name" in samples[0]

@pytest.mark.asyncio
async def test_api_health_endpoint(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    health = response.json()
    assert health["status"] == "healthy"
    assert "concurrency_limit" in health

@pytest.mark.asyncio
async def test_api_idempotency_header_prevents_duplicate_work(async_client, sample_image_bytes):
    payload = {
        "image_url": "https://example.com/item.png",
        "product_name": "Idempotent Product",
        "product_description": "A product used to verify duplicate protection.",
        "target_audience": "API testers",
        "key_benefits": ["Only generated once"],
        "tone": "Direct",
    }
    with patch(
        "app.services.orchestrator.download_and_validate_image",
        new_callable=AsyncMock,
        return_value=sample_image_bytes,
    ):
        first = await async_client.post(
            "/api/generations",
            json=payload,
            headers={"Idempotency-Key": "api-idempotency-test"},
        )
        second = await async_client.post(
            "/api/generations",
            json=payload,
            headers={"Idempotency-Key": "api-idempotency-test"},
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert len(orchestrator.records) == 1

@pytest.mark.asyncio
async def test_api_returns_429_when_queue_is_full(async_client):
    orchestrator.pending_count = settings.MAX_QUEUE_SIZE
    payload = {
        "image_url": "https://example.com/item.png",
        "product_name": "Capacity Product",
        "product_description": "A product used to verify queue admission.",
        "target_audience": "API testers",
        "key_benefits": ["Predictable capacity"],
        "tone": "Direct",
    }

    response = await async_client.post("/api/generations", json=payload)

    assert response.status_code == 429
    assert "capacity reached" in response.json()["detail"].lower()
