import json
import asyncio
import httpx
from app.services.providers.base import BaseAIProvider
from app.schemas.generation import ProductContext, CreativeOutput
from app.services.prompt_engine import SYSTEM_INSTRUCTION, build_copy_prompt
from app.core.config import settings
from app.core.exceptions import PermanentError, TemporaryError

class GeminiAIProvider(BaseAIProvider):
    """
    Google Gemini provider using structured JSON output.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL

        if not self.api_key:
            raise PermanentError("GEMINI_API_KEY environment variable is not configured.")

    @property
    def model_name(self) -> str:
        return f"gemini/{self.model}"

    async def generate_ad_copy(self, context: ProductContext) -> CreativeOutput:
        prompt_text = build_copy_prompt(context)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 429:
                    raise TemporaryError("Gemini API rate limit exceeded (429).")
                elif response.status_code in (500, 502, 503, 504):
                    raise TemporaryError(f"Gemini API temporary server error ({response.status_code}).")
                elif response.status_code >= 400:
                    data = response.json() if response.content else {}
                    err_msg = data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    raise PermanentError(f"Gemini API rejected request: {err_msg}")

                result = response.json()
                candidates = result.get("candidates", [])
                if not candidates:
                    raise PermanentError("Gemini returned empty candidate response.")

                content_parts = candidates[0].get("content", {}).get("parts", [])
                if not content_parts or "text" not in content_parts[0]:
                    raise PermanentError("Gemini returned malformed response text.")

                raw_json = content_parts[0]["text"]
                parsed = json.loads(raw_json)

                return CreativeOutput(
                    headline=parsed["headline"],
                    supporting_text=parsed["supporting_text"],
                    cta=parsed["cta"],
                    visual_direction=parsed.get("visual_direction", "Modern studio product showcase")
                )

        except (PermanentError, TemporaryError):
            raise
        except httpx.TimeoutException:
            raise TemporaryError(f"Gemini request timed out after {settings.PROVIDER_TIMEOUT_SECONDS}s.")
        except json.JSONDecodeError as e:
            raise PermanentError(f"Failed to parse Gemini response as JSON: {str(e)}")
        except Exception as e:
            raise TemporaryError(f"Gemini provider error: {str(e)}")
