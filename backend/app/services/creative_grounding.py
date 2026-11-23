import re
from app.schemas.generation import ProductContext, CreativeOutput
from app.core.exceptions import PermanentError

HALLUCINATION_TRIGGERS = [
    r"\b\d+%\s*off\b",
    r"\bfree\s+shipping\b",
    r"\bfda\s+approved\b",
    r"\blifetime\s+warranty\b",
    r"\b#1\s+rated\b",
    r"\bworld['’]?s\s+best\b",
    r"\bcelebrity\s+endorsed\b",
    r"\bmoney\s+back\s+guarantee\b",
    r"\bclinically\s+proven\b",
]

def validate_creative_grounding(context: ProductContext, creative: CreativeOutput) -> None:
    """
    Validates that the generated creative copy adheres to strict word limits
    and does not hallucinate unauthorized claims not present in source context.
    """
    # 1. Word counts
    h_words = len(creative.headline.strip().split())
    if h_words > 8:
        raise PermanentError(f"Grounded copy validation failed: Headline exceeds 8 words limit ({h_words} words).")
    
    s_words = len(creative.supporting_text.strip().split())
    if s_words > 20:
        raise PermanentError(f"Grounded copy validation failed: Supporting text exceeds 20 words limit ({s_words} words).")
        
    c_words = len(creative.cta.strip().split())
    if c_words > 4:
        raise PermanentError(f"Grounded copy validation failed: CTA exceeds 4 words limit ({c_words} words).")

    # 2. Check for invented marketing gimmicks not present in the input context
    context_corpus = f"{context.product_name} {context.product_description} {context.target_audience} {' '.join(context.key_benefits)} {context.tone}".lower()
    combined_ad_copy = f"{creative.headline} {creative.supporting_text} {creative.cta}".lower()

    for pattern in HALLUCINATION_TRIGGERS:
        match = re.search(pattern, combined_ad_copy)
        if match:
            matched_phrase = match.group(0)
            # If the phrase was NOT part of the input context, it is a hallucination
            if not re.search(pattern, context_corpus):
                raise PermanentError(
                    f"Grounded copy validation failed: Ungrounded claim '{matched_phrase}' detected in generated copy."
                )
