from app.core.config import settings
from app.services.providers.base import BaseAIProvider
from app.services.providers.fake_provider import FakeAIProvider
from app.services.providers.gemini_provider import GeminiAIProvider
from app.services.providers.openai_provider import OpenAIAIProvider

def get_provider(provider_name: str = None) -> BaseAIProvider:
    name = (provider_name or settings.AI_PROVIDER).lower()
    if name == "fake":
        return FakeAIProvider()
    elif name == "gemini":
        return GeminiAIProvider()
    elif name == "openai":
        return OpenAIAIProvider()
    else:
        raise ValueError(f"Unknown AI Provider '{name}'. Allowed: fake, gemini, openai.")
