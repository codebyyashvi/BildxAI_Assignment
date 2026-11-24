"""
API route tests using Starlette's synchronous TestClient.
This avoids Windows event-loop hangs entirely.
"""
import time
from unittest.mock import patch, AsyncMock
from app.services.orchestrator import orchestrator, GenerationOrchestrator
from app.schemas.generation import GenerationStatus
from app.core.config import settings


def test_full_ad_generation_flow(sync_client, sample_image_bytes):
    """POST /generations -> poll until COMPLETED -> download image."""
    with patch("app.services.orchestrator.download_and_validate_image", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = sample_image_bytes
        payload = {
            "image_url": "https://bildx.ai/samples/assets/roam-front.webp",
            "product_name": "ROAM Lock 750",
            "product_description": "A 750 ml insulated steel tumbler with a locking sip lid.",
            "target_audience": "Commuters and hikers",
            "key_benefits": ["Up to 12 hours cold", "Carry loop", "Locking lid"],
            "tone": "Adventurous and practical",
            "idempotency_key": "test-flow-sync-key-1"
        }

        # 1. Enqueue
        response = sync_client.post("/api/generations", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        gen_id = data["id"]
        assert data["status"] in ("pending", "processing")

        # 2. Poll until COMPLETED (background task runs in TestClient's event loop)
        completed = False
        for _ in range(60):
            poll = sync_client.get(f"/api/generations/{gen_id}")
            assert poll.status_code == 200
            poll_data = poll.json()
            if poll_data["status"] == GenerationStatus.COMPLETED.value:
                completed = True
                assert poll_data["creative_output"] is not None
                assert "headline" in poll_data["creative_output"]
                assert "supporting_text" in poll_data["creative_output"]
                assert "cta" in poll_data["creative_output"]
                assert poll_data["image_url"] is not None
                break
            elif poll_data["status"] == GenerationStatus.FAILED.value:
                import pytest
                pytest.fail(f"Generation failed prematurely: {poll_data.get('error_message')}")
            time.sleep(0.05)

        assert completed, "Generation did not reach COMPLETED state within allotted time"

        # 3. Download generated image
        img_resp = sync_client.get(f"/api/generations/{gen_id}/image")
        assert img_resp.status_code == 200
        assert img_resp.headers["content-type"] == "image/png"
        assert len(img_resp.content) > 0


def test_api_validation_error(sync_client):
    """Missing required fields must return 422."""
    bad_payload = {
        "image_url": "https://example.com/item.png",
        "product_name": ""
    }
    response = sync_client.post("/api/generations", json=bad_payload)
    assert response.status_code == 422


def test_api_samples_endpoint(sync_client):
    response = sync_client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert isinstance(samples, list)
    assert len(samples) >= 1
    assert "product_name" in samples[0]


def test_api_health_endpoint(sync_client):
    response = sync_client.get("/api/health")
    assert response.status_code == 200
    health = response.json()
    assert health["status"] == "healthy"
    assert "concurrency_limit" in health


def test_api_idempotency_header_prevents_duplicate_work(sync_client, sample_image_bytes):
    """Two requests with the same Idempotency-Key must return the same generation ID."""
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
        first = sync_client.post(
            "/api/generations",
            json=payload,
            headers={"Idempotency-Key": "api-idempotency-sync-test"},
        )
        second = sync_client.post(
            "/api/generations",
            json=payload,
            headers={"Idempotency-Key": "api-idempotency-sync-test"},
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


def test_api_returns_429_when_queue_is_full(sync_client):
    """When pending_count >= MAX_QUEUE_SIZE, the API must return 429."""
    saved = orchestrator.pending_count
    orchestrator.pending_count = settings.MAX_QUEUE_SIZE
    try:
        payload = {
            "image_url": "https://example.com/item.png",
            "product_name": "Capacity Product",
            "product_description": "A product used to verify queue admission.",
            "target_audience": "API testers",
            "key_benefits": ["Predictable capacity"],
            "tone": "Direct",
        }
        response = sync_client.post("/api/generations", json=payload)
        assert response.status_code == 429
        assert "capacity reached" in response.json()["detail"].lower()
    finally:
        orchestrator.pending_count = saved
