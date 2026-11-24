import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import settings
from app.core.exceptions import TemporaryError
from app.schemas.generation import GenerationStatus, ProductContext
from app.services.orchestrator import GenerationOrchestrator
from app.services.providers.openai_provider import OpenAIAIProvider


def context(name: str) -> ProductContext:
    return ProductContext(
        image_url="https://example.com/product.png",
        product_name=name,
        product_description="A factual test product description.",
        target_audience="Careful testers",
        key_benefits=["Predictable behavior"],
        tone="Direct",
    )


async def wait_for_terminal(orch: GenerationOrchestrator, generation_id: str):
    for _ in range(100):
        record = orch.get_generation(generation_id)
        if record.status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
            return record
        await asyncio.sleep(0.02)
    pytest.fail("Generation did not reach a terminal status")


@pytest.mark.asyncio
async def test_temporary_provider_error_is_retried(sample_image_bytes):
    orch = GenerationOrchestrator()
    with patch(
        "app.services.orchestrator.download_and_validate_image",
        new_callable=AsyncMock,
        return_value=sample_image_bytes,
    ):
        record = await orch.create_generation(context("Trigger-Temporary-Error Item"))
        completed = await wait_for_terminal(orch, record.id)

    assert completed.status == GenerationStatus.COMPLETED
    assert completed.metadata.retry_count == 1


@pytest.mark.asyncio
async def test_permanent_provider_error_is_not_retried(sample_image_bytes):
    orch = GenerationOrchestrator()
    with patch(
        "app.services.orchestrator.download_and_validate_image",
        new_callable=AsyncMock,
        return_value=sample_image_bytes,
    ):
        record = await orch.create_generation(context("Trigger-Permanent-Error Item"))
        failed = await wait_for_terminal(orch, record.id)

    assert failed.status == GenerationStatus.FAILED
    assert failed.metadata.retry_count == 0
    assert "permanent provider failure" in failed.error_message.lower()


@pytest.mark.asyncio
async def test_openai_provider_timeout_is_temporary():
    provider = OpenAIAIProvider(api_key="test-key", model="test-model")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("timed out")
        with pytest.raises(TemporaryError) as exc_info:
            await provider.generate_ad_copy(context("Timeout Item"))

    assert str(settings.PROVIDER_TIMEOUT_SECONDS) in exc_info.value.message
