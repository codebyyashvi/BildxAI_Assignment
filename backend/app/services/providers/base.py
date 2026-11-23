from abc import ABC, abstractmethod
from app.schemas.generation import ProductContext, CreativeOutput

class BaseAIProvider(ABC):
    """Abstract interface for AI model providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or identifier of the active model."""
        pass

    @abstractmethod
    async def generate_ad_copy(self, context: ProductContext) -> CreativeOutput:
        """
        Generate grounded advertising copy (headline, supporting text, CTA, visual direction)
        from structured product context.
        """
        pass
