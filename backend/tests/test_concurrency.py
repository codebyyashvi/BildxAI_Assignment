import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from app.services.orchestrator import GenerationOrchestrator
from app.schemas.generation import ProductContext, GenerationStatus
from app.core.exceptions import CapacityExceededError

@pytest.fixture
def test_orchestrator():
    return GenerationOrchestrator()

@pytest.mark.asyncio
async def test_duplicate_idempotency_key(test_orchestrator, sample_image_bytes):
    context = ProductContext(
        image_url="https://example.com/item.png",
        product_name="Idempotency Item",
        product_description="A test product description.",
        target_audience="Testers",
        key_benefits=["Benefit 1"],
        tone="Direct"
    )

    with patch("app.services.orchestrator.download_and_validate_image", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = sample_image_bytes
        # First submission with key "idem-key-123"
        rec1 = await test_orchestrator.create_generation(context, idempotency_key="idem-key-123")
        # Second submission with the exact same key
        rec2 = await test_orchestrator.create_generation(context, idempotency_key="idem-key-123")

        # Must return the identical generation ID without starting duplicate work
        assert rec1.id == rec2.id

@pytest.mark.asyncio
async def test_capacity_rejection_at_limit(test_orchestrator):
    context = ProductContext(
        image_url="https://example.com/item.png",
        product_name="Capacity Item",
        product_description="A test product description.",
        target_audience="Testers",
        key_benefits=["Benefit 1"],
        tone="Direct"
    )

    # Artificially fill pending queue to max
    test_orchestrator.pending_count = 5 # matching settings.MAX_QUEUE_SIZE
    with patch("app.core.config.settings.MAX_QUEUE_SIZE", 5):
        with pytest.raises(CapacityExceededError) as exc_info:
            await test_orchestrator.create_generation(context)
        assert "capacity reached" in exc_info.value.message.lower()

@pytest.mark.asyncio
async def test_concurrent_requests_and_failure_isolation(sample_image_bytes):
    orch = GenerationOrchestrator()
    orch.semaphore = asyncio.Semaphore(3)

    normal_context = ProductContext(
        image_url="https://example.com/normal.png",
        product_name="ROAM Normal Tumbler",
        product_description="A 750 ml tumbler.",
        target_audience="Commuters",
        key_benefits=["12h cold"],
        tone="Adventurous"
    )

    # Product triggering simulated permanent failure
    failing_context = ProductContext(
        image_url="https://example.com/fail.png",
        product_name="Trigger-Permanent-Error Item",
        product_description="An item designed to fail.",
        target_audience="Testers",
        key_benefits=["Fails gracefully"],
        tone="Critical"
    )

    with patch("app.services.orchestrator.download_and_validate_image", new_callable=AsyncMock) as mock_dl:
        mock_dl.return_value = sample_image_bytes
        # Launch 5 normal tasks and 1 failing task concurrently
        rec_fail = await orch.create_generation(failing_context)

        normal_recs = []
        for i in range(5):
            rec = await orch.create_generation(normal_context)
            normal_recs.append(rec)

        # Wait for all background tasks to settle
        max_wait = 50
        while max_wait > 0:
            all_done = (
                orch.get_generation(rec_fail.id).status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED)
                and all(orch.get_generation(r.id).status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED) for r in normal_recs)
            )
            if all_done:
                break
            await asyncio.sleep(0.05)
            max_wait -= 1

        # Assert failure isolation: failing job ended with FAILED status
        final_fail = orch.get_generation(rec_fail.id)
        assert final_fail.status == GenerationStatus.FAILED
        assert "Simulated permanent provider failure" in final_fail.error_message

        # Assert normal jobs all completed successfully despite the failing peer
        for r in normal_recs:
            final_norm = orch.get_generation(r.id)
            assert final_norm.status == GenerationStatus.COMPLETED
            assert final_norm.creative_output is not None
            assert final_norm.image_relative_path is not None
