from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings
from app.engine import narrative


class Translator(ABC):
    name: str = "local"

    @abstractmethod
    async def translate(self, text: str, target_lang: str) -> str | None:
        ...


class LocalTranslator(Translator):
    name = "local"

    async def translate(self, text: str, target_lang: str) -> str | None:
        return None


class AzureTranslator(Translator):
    name = "azure"

    def __init__(self, endpoint: str, key: str, region: str = "") -> None:
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.region = region

    def _headers(self) -> dict[str, str]:
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/json",
        }
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        return headers

    async def translate(self, text: str, target_lang: str) -> str | None:
        import httpx

        if not self.key:
            return None
        code = "en" if target_lang.startswith("en") else narrative_translator_code(target_lang)
        url = f"{self.endpoint}/translate?api-version=3.0&to={code}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=self._headers(), json=[{"text": text}])
                response.raise_for_status()
                data = response.json()
                return data[0]["translations"][0]["text"]
        except Exception:
            return None


def narrative_translator_code(lang: str) -> str:
    mapping = {
        "es": "es",
        "fr": "fr",
        "pt": "pt",
        "ar": "ar",
        "zu": "zu",
        "en": "en",
    }
    return mapping.get(lang, lang)


@lru_cache
def get_translator() -> Translator:
    settings = get_settings()
    if settings.translator_provider == "azure" and settings.azure_translator_ready:
        return AzureTranslator(
            settings.azure_translator_endpoint,
            settings.azure_translator_key,
            settings.azure_translator_region,
        )
    return LocalTranslator()
