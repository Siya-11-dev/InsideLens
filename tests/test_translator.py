import asyncio

from app.config import Settings
from app.llm.translator import (
    AzureTranslator,
    LocalTranslator,
    get_translator,
    narrative_translator_code,
)


def test_local_translator_returns_none():
    assert asyncio.run(LocalTranslator().translate("hello", "es")) is None


def test_translator_code_mapping():
    assert narrative_translator_code("zu") == "zu"
    assert narrative_translator_code("en") == "en"
    assert narrative_translator_code("xx") == "xx"


def test_azure_translator_without_key_returns_none():
    assert asyncio.run(AzureTranslator("https://api.example.com", "").translate("hi", "es")) is None


def test_azure_translator_parses_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"translations": [{"text": "Hola"}]}]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            assert "to=es" in url
            assert headers["Ocp-Apim-Subscription-Key"] == "key"
            return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    translator = AzureTranslator("https://api.example.com", "key", region="westeurope")
    assert asyncio.run(translator.translate("hello", "es")) == "Hola"


def test_factory_defaults_to_local(monkeypatch):
    get_translator.cache_clear()
    monkeypatch.setattr("app.llm.translator.get_settings", lambda: Settings())
    assert get_translator().name == "local"
    get_translator.cache_clear()
