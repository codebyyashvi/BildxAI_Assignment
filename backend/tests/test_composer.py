import io
from pathlib import Path
from PIL import Image
from app.schemas.generation import ProductContext, CreativeOutput
from app.services.composer import compose_advertisement, CANVAS_WIDTH, CANVAS_HEIGHT

def test_compose_advertisement(tmp_path: Path, sample_image_bytes: bytes):
    context = ProductContext(
        image_url="https://bildx.ai/samples/assets/roam-front.webp",
        product_name="ROAM Lock 750",
        product_description="A 750 ml insulated steel tumbler with a locking sip lid.",
        target_audience="Commuters and hikers",
        key_benefits=["Up to 12 hours cold", "Carry loop", "Locking lid"],
        tone="Adventurous and practical"
    )
    creative = CreativeOutput(
        headline="Lock it. Loop it. Go.",
        supporting_text="Cold drinks for commutes, workouts and days outside.",
        cta="Explore ROAM",
        visual_direction="Premium outdoor travel scene"
    )

    output_file = tmp_path / "test_ad.png"
    result_path = compose_advertisement(
        product_image_bytes=sample_image_bytes,
        context=context,
        creative=creative,
        output_path=output_file
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    # Verify generated dimensions
    with Image.open(result_path) as img:
        assert img.width == CANVAS_WIDTH
        assert img.height == CANVAS_HEIGHT
        assert img.format == "PNG"
