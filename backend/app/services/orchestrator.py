import asyncio
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.core.config import settings
from app.core.exceptions import (
    AdGenException,
    TemporaryError,
    PermanentError,
    CapacityExceededError,
    GenerationNotFoundError
)
from app.schemas.generation import (
    GenerationStatus,
    GenerationRecord,
    GenerationMetadata,
    ProductContext,
    CreativeOutput
)
from app.services.prompt_engine import PROMPT_VERSION
from app.services.creative_grounding import validate_creative_grounding
from app.services.image_downloader import download_and_validate_image
from app.services.composer import compose_advertisement
from app.services.providers import get_provider

class GenerationOrchestrator:
    """
    Central orchestration engine managing concurrency, rate limits,
    idempotency, bounded retries, failure isolation, and lifecycle status tracking.
    """

    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GENERATIONS)
        self.records: Dict[str, GenerationRecord] = {}
        self.idempotency_map: Dict[str, str] = {} # idempotency_key -> generation_id
        self.pending_count = 0
        self.active_provider_calls = 0
        self._lock = asyncio.Lock()

    def get_generation(self, generation_id: str) -> GenerationRecord:
        record = self.records.get(generation_id)
        if not record:
            raise GenerationNotFoundError(generation_id)
        return record

    async def create_generation(
        self,
        context: ProductContext,
        idempotency_key: Optional[str] = None,
        allow_local_for_testing: bool = False
    ) -> GenerationRecord:
        """
        Accepts a generation request with capacity checks and duplicate protection.
        Returns immediately with a pending record while work executes asynchronously.
        """
        async with self._lock:
            # 1. Idempotency Check
            if idempotency_key:
                clean_key = idempotency_key.strip()
                if clean_key in self.idempotency_map:
                    existing_id = self.idempotency_map[clean_key]
                    existing_record = self.records.get(existing_id)
                    if existing_record:
                        # Return existing generation without repeating work
                        return existing_record

            # 2. Capacity Limit Check
            if self.pending_count >= settings.MAX_QUEUE_SIZE:
                raise CapacityExceededError(
                    f"System capacity reached. Maximum queue depth of {settings.MAX_QUEUE_SIZE} exceeded."
                )

            generation_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            record = GenerationRecord(
                id=generation_id,
                status=GenerationStatus.PENDING,
                context=context,
                created_at=now,
                updated_at=now,
                metadata=GenerationMetadata(
                    model=settings.AI_PROVIDER,
                    prompt_version=PROMPT_VERSION,
                    source_url=context.image_url,
                    created_at=now,
                    idempotency_key=idempotency_key
                )
            )

            self.records[generation_id] = record
            if idempotency_key:
                self.idempotency_map[idempotency_key.strip()] = generation_id

            self.pending_count += 1

        # Launch background task for failure-isolated execution
        asyncio.create_task(self._process_generation(generation_id, allow_local_for_testing))
        return record

    async def _process_generation(self, generation_id: str, allow_local_for_testing: bool):
        """
        Worker routine executed inside its own isolated asyncio task.
        Bounded by semaphore concurrency, with transient retry loops and safety bounds.
        """
        record = self.records.get(generation_id)
        if not record:
            return

        start_time = time.perf_counter()

        try:
            # Wait for available concurrency slot
            async with self.semaphore:
                async with self._lock:
                    self.pending_count = max(0, self.pending_count - 1)
                    self.active_provider_calls += 1
                    record.status = GenerationStatus.PROCESSING
                    record.updated_at = datetime.now(timezone.utc)

                try:
                    # Step 1: Download & Validate Source Product Image
                    image_bytes = await download_and_validate_image(
                        record.context.image_url,
                        allow_local_for_testing=allow_local_for_testing
                    )

                    # Step 2: Generate Grounded Creative Copy with Bounded Retries
                    provider = get_provider()
                    if record.metadata:
                        record.metadata.model = provider.model_name

                    creative: Optional[CreativeOutput] = None
                    retries = 0

                    while True:
                        try:
                            creative = await provider.generate_ad_copy(record.context)
                            break
                        except TemporaryError as te:
                            if retries < settings.MAX_RETRIES:
                                retries += 1
                                record.status = GenerationStatus.RETRYING
                                if record.metadata:
                                    record.metadata.retry_count = retries
                                record.updated_at = datetime.now(timezone.utc)

                                backoff_delay = settings.RETRY_BACKOFF_BASE * (2 ** (retries - 1))
                                await asyncio.sleep(backoff_delay)
                                continue
                            else:
                                raise TemporaryError(f"Temporary provider error exhausted max retries ({settings.MAX_RETRIES}): {te.message}")
                        except PermanentError:
                            # Permanent errors must NOT be retried
                            raise

                    # Step 3: Verify Creative Grounding and Guardrails
                    validate_creative_grounding(record.context, creative)
                    record.creative_output = creative

                    # Step 4: Compose Final Advertisement Image
                    output_filename = f"{generation_id}.png"
                    output_file_path = settings.STORAGE_DIR / output_filename
                    compose_advertisement(
                        product_image_bytes=image_bytes,
                        context=record.context,
                        creative=creative,
                        output_path=output_file_path
                    )
                    record.image_relative_path = output_filename

                    # Mark Success
                    end_time = time.perf_counter()
                    record.status = GenerationStatus.COMPLETED
                    record.updated_at = datetime.now(timezone.utc)
                    if record.metadata:
                        record.metadata.completed_at = record.updated_at
                        record.metadata.execution_time_ms = round((end_time - start_time) * 1000, 2)

                finally:
                    async with self._lock:
                        self.active_provider_calls = max(0, self.active_provider_calls - 1)

        except PermanentError as pe:
            record.status = GenerationStatus.FAILED
            record.error_message = pe.message
            record.updated_at = datetime.now(timezone.utc)
        except TemporaryError as te:
            record.status = GenerationStatus.FAILED
            record.error_message = te.message
            record.updated_at = datetime.now(timezone.utc)
        except Exception as e:
            # Shield internal stack traces and configuration from leaking
            record.status = GenerationStatus.FAILED
            record.error_message = f"Generation failed unexpectedly: {type(e).__name__}"
            record.updated_at = datetime.now(timezone.utc)

# Global singleton orchestrator
orchestrator = GenerationOrchestrator()
