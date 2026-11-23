import json
import httpx
from app.services.providers.base import BaseAIProvider
from app.schemas.generation import ProductContext, CreativeOutput
from app.services.prompt_engine import SYSTEM_INSTRUCTION, build_copy_prompt
from app.core.config import settings
from app.core.exceptions import PermanentError, TemporaryError

class OpenAIAIProvider(BaseAIProvider):
    """
    OpenAI provider using chat completions with JSON mode.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL

        if not self.api_key:
            raise PermanentError("OPENAI_API_KEY environment variable is not configured.")

    @property
    def model_name(self) -> str:
        return f"openai/{self.model}"

    async def generate_ad_copy(self, context: ProductContext) -> CreativeOutput:
        prompt_text = build_copy_prompt(context)
        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt_text}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 429:
                    raise TemporaryError("OpenAI API rate limit exceeded (429).")
                elif response.status_code in (500, 502, 503, 504):
                    raise TemporaryError(f"OpenAI API temporary server error ({response.status_code}).")
                elif response.status_code >= 400:
                    data = response.json() if response.content else {}
                    err_msg = data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    raise PermanentError(f"OpenAI API rejected request: {err_msg}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                return CreativeOutput(
                    headline=parsed["headline"],
                    supporting_text=parsed["supporting_text"],
                    cta=parsed["cta"],
                    visual_direction=parsed.get("visual_direction", "Modern studio product showcase")
                )

        except (PermanentError, TemporaryError):
            raise
        except httpx.TimeoutException:
            raise TemporaryError(f"OpenAI request timed out after {settings.PROVIDER_TIMEOUT_SECONDS}s.")
        except json.JSONDecodeError as e:
            raise PermanentError(f"Failed to parse OpenAI response as JSON: {str(e)}")
        except Exception as e:
            raise TemporaryError(f"OpenAI provider error: {str(e)}")
