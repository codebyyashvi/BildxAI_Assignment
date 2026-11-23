import asyncio
from app.services.providers.base import BaseAIProvider
from app.schemas.generation import ProductContext, CreativeOutput
from app.core.exceptions import TemporaryError, PermanentError
from app.core.config import settings

class FakeAIProvider(BaseAIProvider):
    """
    Fake / Mock AI Provider for automated tests, demonstrations, and offline operation.
    Requires zero API keys and consumes zero paid credits.
    """

    def __init__(self, delay_seconds: float = None):
        self.delay = delay_seconds if delay_seconds is not None else settings.FAKE_PROVIDER_DELAY_SECONDS
        self._temporary_failure_attempts = {}

    @property
    def model_name(self) -> str:
        return "fake-grounded-copy-v1"

    async def generate_ad_copy(self, context: ProductContext) -> CreativeOutput:
        # Simulate configurable latency
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # Trigger simulated permanent failure if requested by test input
        if "Trigger-Permanent-Error" in context.product_name:
            raise PermanentError("Simulated permanent provider failure: Invalid model parameters.")

        # Trigger simulated temporary failure (fails on first call, succeeds on retry)
        if "Trigger-Temporary-Error" in context.product_name:
            count = self._temporary_failure_attempts.get(context.product_name, 0)
            if count == 0:
                self._temporary_failure_attempts[context.product_name] = count + 1
                raise TemporaryError("Simulated temporary provider timeout: Gateway timeout (504).")

        # Deterministically craft grounded ad copy respecting all limits
        # 1. Headline (<= 8 words)
        if "roam" in context.product_name.lower():
            headline = "Lock it. Loop it. Go."
        else:
            first_benefit = context.key_benefits[0] if context.key_benefits else "Built to perform"
            # Keep headline punchy
            clean_benefit = first_benefit.replace("Up to ", "").replace(" hours", "hr")
            headline = f"{context.product_name}: {clean_benefit}".strip()
            headline_words = headline.split()
            if len(headline_words) > 8:
                headline = " ".join(headline_words[:8])

        # 2. Supporting text (<= 20 words)
        benefits_summary = ", ".join(context.key_benefits[:2])
        supporting_text = f"Designed for {context.target_audience}. Featuring {benefits_summary} for daily reliability."
        s_words = supporting_text.split()
        if len(s_words) > 20:
            supporting_text = " ".join(s_words[:20])

        # 3. CTA (<= 4 words)
        cta = f"Shop {context.product_name.split()[0]}"
        c_words = cta.split()
        if len(c_words) > 4:
            cta = " ".join(c_words[:4])

        # 4. Visual direction
        visual_direction = f"Clean {context.tone.lower()} commercial showcase highlighting {context.product_name}"

        return CreativeOutput(
            headline=headline,
            supporting_text=supporting_text,
            cta=cta,
            visual_direction=visual_direction
        )
