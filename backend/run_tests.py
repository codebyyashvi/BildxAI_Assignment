import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import asyncio
import io
import time
from PIL import Image

from app.core.config import settings
# Set test environment to skip live DNS
settings.ENVIRONMENT = "test"
settings.AI_PROVIDER = "fake"
settings.FAKE_PROVIDER_DELAY_SECONDS = 0.01

from app.core.security import validate_image_url
from app.core.exceptions import PermanentError, CapacityExceededError
from app.schemas.generation import ProductContext, CreativeOutput, GenerationStatus
from app.services.creative_grounding import validate_creative_grounding
from app.services.composer import compose_advertisement, CANVAS_WIDTH, CANVAS_HEIGHT
from app.services.providers.fake_provider import FakeAIProvider
from app.services.orchestrator import GenerationOrchestrator
import app.services.orchestrator as orch_module

def make_sample_image() -> bytes:
    img = Image.new("RGBA", (300, 300), color=(50, 120, 220, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

async def test_all():
    print("=" * 60, flush=True)
    print("BILDX AI - AUTOMATED TEST SUITE", flush=True)
    print("=" * 60, flush=True)

    # 1. Grounding Tests
    print("\n[1/5] Testing Creative Grounding & Safety Rules...", flush=True)
    ctx = ProductContext(
        image_url="https://bildx.ai/samples/assets/roam-front.webp",
        product_name="ROAM Lock 750",
        product_description="A 750 ml insulated steel tumbler with a locking sip lid.",
        target_audience="Commuters, gym users and day hikers",
        key_benefits=["Up to 12 hours cold", "Carry loop", "Locking lid"],
        tone="Adventurous and practical"
    )
    valid_creative = CreativeOutput(
        headline="Lock it. Loop it. Go.",
        supporting_text="Cold drinks for commutes, workouts and days outside.",
        cta="Explore ROAM",
        visual_direction="Premium outdoor travel scene"
    )
    validate_creative_grounding(ctx, valid_creative)
    print("  ✓ Valid grounded copy passed", flush=True)

    # Word limits
    try:
        CreativeOutput(
            headline="One two three four five six seven eight nine",
            supporting_text="valid", cta="shop", visual_direction="dir"
        )
        assert False, "Should have failed on headline > 8 words"
    except ValueError:
        print("  ✓ Headline word limit (<=8 words) enforced", flush=True)

    try:
        CreativeOutput(
            headline="Headline",
            supporting_text=" ".join(["word"] * 21),
            cta="shop", visual_direction="dir"
        )
        assert False, "Should have failed on supporting_text > 20 words"
    except ValueError:
        print("  ✓ Supporting text limit (<=20 words) enforced", flush=True)

    try:
        CreativeOutput(
            headline="Headline", supporting_text="Text",
            cta="Shop The Super Roam Today", # 5 words
            visual_direction="dir"
        )
        assert False, "Should have failed on CTA > 4 words"
    except ValueError:
        print("  ✓ CTA limit (<=4 words) enforced", flush=True)

    # Ungrounded claim / Hallucination detection
    hallucinated = CreativeOutput(
        headline="Get 50% Off Today",
        supporting_text="Cold drinks for commutes.",
        cta="Shop ROAM",
        visual_direction="Scene"
    )
    try:
        validate_creative_grounding(ctx, hallucinated)
        assert False, "Should have caught hallucinated claim"
    except PermanentError:
        print("  ✓ Ungrounded claim ('50% off') caught and rejected", flush=True)

    # 2. SSRF & Security Tests
    print("\n[2/5] Testing Security & SSRF Protection...", flush=True)
    for bad_url in [
        "http://localhost:8000/image.png",
        "http://127.0.0.1/evil.png",
        "http://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd"
    ]:
        try:
            validate_image_url(bad_url)
            assert False, f"Should have blocked {bad_url}"
        except PermanentError:
            pass
    print("  ✓ SSRF blocked for localhost, 127.0.0.1, link-local metadata, file:// schemes", flush=True)

    # 3. Provider & Fake Generation Test
    print("\n[3/5] Testing Fake Provider & Grounded Generation...", flush=True)
    provider = FakeAIProvider(delay_seconds=0.01)
    gen_creative = await provider.generate_ad_copy(ctx)
    assert gen_creative.headline
    assert gen_creative.supporting_text
    assert gen_creative.cta
    validate_creative_grounding(ctx, gen_creative)
    print(f"  ✓ Generated: Headline='{gen_creative.headline}', CTA='{gen_creative.cta}'", flush=True)

    # 4. Compositor Test
    print("\n[4/5] Testing Visual Image Compositor...", flush=True)
    sample_bytes = make_sample_image()
    test_out = Path("storage/test_output.png")
    test_out.parent.mkdir(parents=True, exist_ok=True)
    compose_advertisement(sample_bytes, ctx, valid_creative, test_out)
    assert test_out.exists()
    with Image.open(test_out) as img:
        assert img.width == CANVAS_WIDTH and img.height == CANVAS_HEIGHT
        assert img.format == "PNG"
    print(f"  ✓ Image composed cleanly: {CANVAS_WIDTH}x{CANVAS_HEIGHT} PNG", flush=True)

    # 5. Concurrency, Queue Limits & Failure Isolation
    print("\n[5/5] Testing Orchestrator Concurrency & Capacity...", flush=True)
    sample_bytes_local = sample_bytes
    async def mock_download(url, allow_local_for_testing=False):
        if "fail-download" in url:
            raise PermanentError("Mock download 404")
        return sample_bytes_local

    # Patch download_and_validate_image on the orchestrator module
    orch_module.download_and_validate_image = mock_download

    orch = GenerationOrchestrator()
    orch.semaphore = asyncio.Semaphore(3)

    # Duplicate idempotency test
    rec_a = await orch.create_generation(ctx, idempotency_key="idempotent-test-key")
    rec_b = await orch.create_generation(ctx, idempotency_key="idempotent-test-key")
    assert rec_a.id == rec_b.id
    print("  ✓ Duplicate Idempotency protection verified (identical generation ID returned)", flush=True)

    # Capacity limit test
    orch.pending_count = settings.MAX_QUEUE_SIZE
    try:
        await orch.create_generation(ctx)
        assert False, "Should have thrown CapacityExceededError"
    except CapacityExceededError:
        print(f"  ✓ Capacity saturation enforced (rejected at queue limit {settings.MAX_QUEUE_SIZE})", flush=True)
    orch.pending_count = 0

    # Concurrent execution + Failure isolation test
    fail_ctx = ProductContext(
        image_url="https://example.com/fail-download.png",
        product_name="Failing Product",
        product_description="Will fail on download.",
        target_audience="Testers",
        key_benefits=["Fails"],
        tone="Test"
    )

    good_recs = [await orch.create_generation(ctx) for _ in range(8)]
    bad_recs = [await orch.create_generation(fail_ctx) for _ in range(2)]

    start = time.perf_counter()
    while True:
        all_finished = (
            all(orch.get_generation(r.id).status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED) for r in good_recs)
            and all(orch.get_generation(r.id).status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED) for r in bad_recs)
        )
        if all_finished or (time.perf_counter() - start > 10):
            break
        await asyncio.sleep(0.02)

    for r in good_recs:
        record = orch.get_generation(r.id)
        assert record.status == GenerationStatus.COMPLETED
        assert record.creative_output is not None
        assert record.image_relative_path is not None

    for r in bad_recs:
        record = orch.get_generation(r.id)
        assert record.status == GenerationStatus.FAILED
        assert record.error_message is not None

    print(f"  ✓ Concurrency & Failure Isolation verified (8 succeeded, 2 failed in isolation)", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("ALL TESTS PASSED PERFECTLY (100% SUCCESS)", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    asyncio.run(test_all())
