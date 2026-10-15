from __future__ import annotations

import httpx

from app.config import Settings
from app.llm.base import LLMClient
from app.models import Insight

_SYSTEM = (
    "You are an elite football broadcast analyst. Given a structured, evidence-backed "
    "insight, write a single punchy, broadcast-ready explanation (2-3 sentences). "
    "Be accurate to the supplied evidence, do not invent facts, and explain WHY the "
    "moment or pattern happened."
)

_LANG_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "ar": "Arabic",
    "zu": "isiZulu",
}


class AzureOpenAIClient(LLMClient):
    name = "azure-openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.url = (
            f"{settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
            f"{settings.azure_openai_deployment}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )
        self.headers = {
            "api-key": settings.azure_openai_api_key,
            "Content-Type": "application/json",
        }

    def _prompt(self, insight: Insight) -> str:
        factors = "\n".join(
            f"- {f.name} (weight {f.weight}, {f.direction}): {f.detail}" for f in insight.factors
        )
        evidence = "\n".join(f"- {e.label}: {e.detail}" for e in insight.evidence)
        return (
            f"Situation: {insight.title}\n"
            f"Claim: {insight.claim}\n"
            f"Confidence: {insight.confidence}\n"
            f"Key factors:\n{factors}\n"
            f"Evidence:\n{evidence}\n"
            f"Counterfactual: {insight.counterfactual}\n\n"
            "Write the broadcast explanation now."
        )

    async def _chat(self, messages: list[dict], temperature: float = 0.4) -> str:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 400,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.url, headers=self.headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def narrate(self, insight: Insight) -> str:
        try:
            return await self._chat(
                [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": self._prompt(insight)},
                ]
            )
        except Exception:
            from app.engine import narrative

            return narrative.render_narrative(insight, "en")

    async def translate(self, text: str, target_lang: str) -> str | None:
        lang = _LANG_NAMES.get(target_lang, target_lang)
        try:
            return await self._chat(
                [
                    {
                        "role": "system",
                        "content": f"Translate the user's football commentary into {lang}. "
                        "Return only the translation.",
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
            )
        except Exception:
            return None

    async def compose(self, system: str, user: str) -> str | None:
        try:
            return await self._chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.5,
            )
        except Exception:
            return None
