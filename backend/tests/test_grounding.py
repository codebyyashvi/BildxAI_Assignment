import pytest
from app.schemas.generation import ProductContext, CreativeOutput
from app.services.creative_grounding import validate_creative_grounding
from app.core.exceptions import PermanentError

def test_grounding_valid_copy():
    context = ProductContext(
        image_url="https://bildx.ai/samples/assets/roam-front.webp",
        product_name="ROAM Lock 750",
        product_description="A 750 ml insulated steel tumbler with a locking sip lid.",
        target_audience="Commuters and hikers",
        key_benefits=["Up to 12 hours cold", "Locking lid"],
        tone="Adventurous"
    )
    creative = CreativeOutput(
        headline="Lock it. Loop it. Go.",
        supporting_text="Cold drinks for daily commutes and trails outside.",
        cta="Explore ROAM",
        visual_direction="Crisp mountain trail backdrop"
    )
    # Should not raise exception
    validate_creative_grounding(context, creative)

def test_grounding_headline_exceeds_eight_words():
    context = ProductContext(
        image_url="https://bildx.ai/samples/assets/roam-front.webp",
        product_name="ROAM Lock 750",
        product_description="A 750 ml insulated steel tumbler.",
        target_audience="Commuters",
        key_benefits=["Locking lid"],
        tone="Adventurous"
    )
    # 9 words in headline
    with pytest.raises(ValueError):
        CreativeOutput(
            headline="One two three four five six seven eight nine",
            supporting_text="Valid short supporting text.",
            cta="Shop Now",
            visual_direction="Studio"
        )

def test_grounding_supporting_text_exceeds_twenty_words():
    with pytest.raises(ValueError):
        CreativeOutput(
            headline="Short Headline",
            supporting_text=" ".join(["word"] * 21),
            cta="Shop Now",
            visual_direction="Studio"
        )

def test_grounding_cta_exceeds_four_words():
    with pytest.raises(ValueError):
        CreativeOutput(
            headline="Short Headline",
            supporting_text="Short supporting text",
            cta="Shop The ROAM Tumbler Today", # 5 words
            visual_direction="Studio"
        )

def test_grounding_hallucination_detection():
    context = ProductContext(
        image_url="https://bildx.ai/samples/assets/roam-front.webp",
        product_name="ROAM Lock 750",
        product_description="A 750 ml insulated steel tumbler.",
        target_audience="Commuters",
        key_benefits=["Locking lid"],
        tone="Adventurous"
    )
    # Creative hallucinates 50% off discount which is not in context
    creative = CreativeOutput(
        headline="Get 50% Off Today",
        supporting_text="Cold drinks for daily commutes.",
        cta="Claim Deal",
        visual_direction="Studio"
    )
    with pytest.raises(PermanentError) as exc_info:
        validate_creative_grounding(context, creative)
    assert "Ungrounded claim" in exc_info.value.message
