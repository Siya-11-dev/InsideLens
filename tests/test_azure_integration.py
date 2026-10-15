import asyncio
import importlib.util
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.models import EvidenceItem, Factor, Insight

settings = get_settings()


def _sample() -> Insight:
    return Insight(
        id="integration-1",
        kind="goal_explanation",
        minute=53,
        team_id="HOME",
        title="Home side's opener explained",
        claim="A high turnover in the final third created a 0.34 xG chance that was converted.",
        factors=[
            Factor(name="High turnover", weight=0.34, direction="supports", detail="regained 32m from goal"),
            Factor(name="Chance quality", weight=0.41, direction="supports", detail="0.34 xG, central"),
        ],
        evidence=[EvidenceItem(label="xG", detail="0.34", event_ids=[512], metric="xg", value=0.34)],
        confidence=0.88,
        counterfactual="Had the defence cleared the second ball, the chance would not have arisen.",
    )


needs_llm = pytest.mark.skipif(
    not (settings.llm_provider == "azure" and settings.azure_llm_ready),
    reason="Azure OpenAI not configured (set INSIDELENS_LLM_PROVIDER=azure + AZURE_OPENAI_*)",
)
needs_translator = pytest.mark.skipif(
    not (settings.translator_provider == "azure" and settings.azure_translator_ready),
    reason="Azure Translator not configured",
)
needs_sql = pytest.mark.skipif(
    not (settings.store_backend == "azuresql" and settings.azure_sql_connection),
    reason="Azure SQL not configured",
)
needs_fabric = pytest.mark.skipif(
    not (settings.store_backend == "fabric" and settings.fabric_connection),
    reason="Fabric / OneLake not configured",
)
needs_eventhub = pytest.mark.skipif(
    not (settings.data_source == "eventhub" and settings.eventhub_ready),
    reason="Azure Event Hubs not configured",
)


def _load_smoke():
    path = Path(__file__).resolve().parents[1] / "scripts" / "azure_smoke.py"
    spec = importlib.util.spec_from_file_location("azure_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_azure_exercise_runs_offline(capsys):
    mod = _load_smoke()
    offline = Settings(
        llm_provider="local",
        translator_provider="local",
        store_backend="memory",
        data_source="synthetic",
    )
    asyncio.run(mod.exercise_llm(offline))
    asyncio.run(mod.exercise_translator(offline))
    mod.exercise_sql(offline)
    mod.exercise_fabric(offline)
    mod.exercise_eventhub(offline)
    out = capsys.readouterr().out
    assert out.count("SKIP") == 5


@needs_llm
def test_azure_openai_narrate_live():
    from app.llm.azure import AzureOpenAIClient

    text = asyncio.run(AzureOpenAIClient(settings).narrate(_sample()))
    assert text and text.strip()


@needs_translator
def test_azure_translator_live():
    from app.llm.translator import AzureTranslator

    translator = AzureTranslator(
        settings.azure_translator_endpoint,
        settings.azure_translator_key,
        settings.azure_translator_region,
    )
    result = asyncio.run(translator.translate("A high turnover led to a goal.", "es"))
    assert result and result.strip()


@needs_sql
def test_azure_sql_save_live():
    from app.store.repository import AzureSqlInsightRepository

    repo = AzureSqlInsightRepository(settings.azure_sql_connection, settings.azure_sql_table)
    if not repo._available:
        pytest.skip("pyodbc not installed")
    assert repo.save_many("SMOKE-TEST", [_sample()]) == 1


@needs_fabric
def test_fabric_upload_live(tmp_path):
    from app.store.repository import FabricOneLakeRepository

    repo = FabricOneLakeRepository(settings.fabric_connection, settings.fabric_container)
    if not repo._available:
        pytest.skip("azure-storage-blob not installed")
    local = tmp_path / "insight.jsonl"
    local.write_text(_sample().model_dump_json() + "\n", encoding="utf-8")
    assert repo.upload_file(str(local), "smoke/test_insight.jsonl") is True


@needs_eventhub
def test_eventhub_connection_live():
    try:
        from azure.eventhub import EventHubProducerClient
    except Exception:
        pytest.skip("azure-eventhub not installed")
    producer = EventHubProducerClient.from_connection_string(
        settings.eventhub_connection, eventhub_name=settings.eventhub_name
    )
    with producer:
        props = producer.get_eventhub_properties()
    assert props.get("partition_ids")
