"""Azure exercise for InsideLens.

Exercises each optional Azure integration through the same code paths the app uses.
Safe to run with no credentials: every provider reports SKIP and the offline
implementation is left untouched.

Usage:
    python scripts/azure_smoke.py

Enable a capability by setting the matching env vars (see .env.example), e.g.
    INSIDELENS_LLM_PROVIDER=azure + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.engine import narrative  # noqa: E402
from app.models import EvidenceItem, Factor, Insight  # noqa: E402

SAMPLE = Insight(
    id="smoke-insight-1",
    kind="goal_explanation",
    minute=53,
    team_id="HOME",
    title="Home side's opener explained",
    claim="A high turnover in the final third created a 0.34 xG chance that was converted.",
    factors=[
        Factor(name="High turnover", weight=0.34, direction="supports", detail="regained 32m from goal"),
        Factor(name="Chance quality", weight=0.41, direction="supports", detail="0.34 xG, central"),
        Factor(name="Finishing", weight=0.25, direction="supports", detail="first-time finish"),
    ],
    evidence=[
        EvidenceItem(label="xG", detail="0.34", event_ids=[512], metric="xg", value=0.34),
        EvidenceItem(label="Press", detail="high press led to turnover", event_ids=[510, 511]),
    ],
    confidence=0.88,
    counterfactual="Had the defence cleared the second ball, the chance would not have arisen.",
)


def report(name: str, status: str, detail: str = "") -> None:
    suffix = f" - {detail}" if detail else ""
    print(f"  [{status:^8}] {name}{suffix}")


async def exercise_llm(settings) -> None:
    if settings.llm_provider != "azure":
        report("Azure OpenAI (narrative)", "SKIP", "INSIDELENS_LLM_PROVIDER != azure")
        return
    if not settings.azure_llm_ready:
        report("Azure OpenAI (narrative)", "SKIP", "endpoint/api key not set")
        return
    from app.llm.azure import AzureOpenAIClient

    client = AzureOpenAIClient(settings)
    text = await client.narrate(SAMPLE)
    fallback = narrative.render_narrative(SAMPLE, "en")
    if text and text != fallback:
        report("Azure OpenAI (narrative)", "PASS", text[:90].replace("\n", " "))
    elif text:
        report("Azure OpenAI (narrative)", "FALLBACK", "returned local template (API unreachable?)")
    else:
        report("Azure OpenAI (narrative)", "FAIL", "empty response")


async def exercise_translator(settings) -> None:
    if settings.translator_provider != "azure":
        report("Azure Translator", "SKIP", "INSIDELENS_TRANSLATOR_PROVIDER != azure")
        return
    if not settings.azure_translator_ready:
        report("Azure Translator", "SKIP", "endpoint/key not set")
        return
    from app.llm.translator import AzureTranslator

    translator = AzureTranslator(
        settings.azure_translator_endpoint,
        settings.azure_translator_key,
        settings.azure_translator_region,
    )
    result = await translator.translate(SAMPLE.claim, "es")
    if result:
        report("Azure Translator", "PASS", result[:90])
    else:
        report("Azure Translator", "FAIL", "returned None (request failed)")


def exercise_sql(settings) -> None:
    if settings.store_backend != "azuresql":
        report("Azure SQL insights", "SKIP", "INSIDELENS_STORE_BACKEND != azuresql")
        return
    if not settings.azure_sql_connection:
        report("Azure SQL insights", "SKIP", "AZURE_SQL_CONNECTION_STRING not set")
        return
    from app.store.repository import AzureSqlInsightRepository

    repo = AzureSqlInsightRepository(settings.azure_sql_connection, settings.azure_sql_table)
    if not repo._available:
        report("Azure SQL insights", "FAIL", "pyodbc not installed (pip install -r requirements-azure.txt)")
        return
    try:
        saved = repo.save_many("SMOKE-TEST", [SAMPLE])
        report("Azure SQL insights", "PASS", f"upserted {saved} insight(s) into '{settings.azure_sql_table}'")
    except Exception as exc:
        report("Azure SQL insights", "FAIL", str(exc)[:120])


def exercise_fabric(settings) -> None:
    if settings.store_backend != "fabric":
        report("Fabric / OneLake upload", "SKIP", "INSIDELENS_STORE_BACKEND != fabric")
        return
    if not settings.fabric_connection:
        report("Fabric / OneLake upload", "SKIP", "AZURE_STORAGE_CONNECTION_STRING not set")
        return
    from app.store.repository import FabricOneLakeRepository

    repo = FabricOneLakeRepository(settings.fabric_connection, settings.fabric_container)
    if not repo._available:
        report("Fabric / OneLake upload", "FAIL", "azure-storage-blob not installed")
        return
    tmp = Path(tempfile.gettempdir()) / "insidelens_smoke.jsonl"
    tmp.write_text(SAMPLE.model_dump_json() + "\n", encoding="utf-8")
    try:
        ok = repo.upload_file(str(tmp), "smoke/insidelens_smoke.jsonl")
        report("Fabric / OneLake upload", "PASS" if ok else "FAIL", "smoke/insidelens_smoke.jsonl")
    except Exception as exc:
        report("Fabric / OneLake upload", "FAIL", str(exc)[:120])


def exercise_eventhub(settings) -> None:
    if settings.data_source != "eventhub":
        report("Azure Event Hubs", "SKIP", "INSIDELENS_DATA_SOURCE != eventhub")
        return
    if not settings.eventhub_ready:
        report("Azure Event Hubs", "SKIP", "connection string/name not set")
        return
    try:
        from azure.eventhub import EventHubProducerClient
    except Exception:
        report("Azure Event Hubs", "FAIL", "azure-eventhub not installed")
        return
    try:
        producer = EventHubProducerClient.from_connection_string(
            settings.eventhub_connection, eventhub_name=settings.eventhub_name
        )
        with producer:
            props = producer.get_eventhub_properties()
        parts = props.get("partition_ids", [])
        report("Azure Event Hubs", "PASS", f"connected to '{settings.eventhub_name}' ({len(parts)} partitions)")
    except Exception as exc:
        report("Azure Event Hubs", "FAIL", str(exc)[:120])


async def main() -> int:
    settings = get_settings()
    print("InsideLens - Azure exercise")
    print(
        f"  providers: llm={settings.llm_provider} "
        f"translator={settings.translator_provider} "
        f"store={settings.store_backend} "
        f"source={settings.data_source}\n"
    )
    await exercise_llm(settings)
    await exercise_translator(settings)
    exercise_sql(settings)
    exercise_fabric(settings)
    exercise_eventhub(settings)
    print("\nLegend: PASS=live Azure call succeeded | FALLBACK=graceful offline path | "
          "SKIP=provider not enabled | FAIL=configured but errored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
