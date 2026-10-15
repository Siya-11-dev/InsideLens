# Azure & Microsoft Fabric mapping

InsideLens runs fully offline for demos, but every integration point is designed to
drop into Azure with a config change. This document maps each capability to the
Microsoft service it targets and shows how to enable it.

## Capability → service mapping

| Capability (hackathon brief) | InsideLens component | Microsoft/Azure service |
|---|---|---|
| Real-time match analytics | `engine/analytics.py`, `engine/pipeline.py` | **Azure Event Hubs** / **Azure Functions** (ingest), WebSocket |
| Explain key moments & tactics | `engine/explain.py`, `engine/patterns.py` | **Microsoft Foundry** models |
| Stories / highlights / recaps | `engine/highlights.py`, `engine/narrative.py` | **Azure OpenAI** on **Microsoft Foundry** |
| Multi-language insights | `engine/i18n.py`, `engine/narrative.py` | **Azure AI Translator** |
| Expand datasets for AI/analytics | `store/dataset.py` | **Microsoft Fabric** (Lakehouse/OneLake), **Azure SQL** |
| Personalized experiences | `engine/personas.py` | Azure OpenAI + persona prompts |
| Persist insights | `store/repository.py` | **Azure SQL Database**, **OneLake** |

## Enabling each service

### 1. LLM (Microsoft Foundry / Azure OpenAI)

```env
INSIDELENS_LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
```

`app/llm/azure.py` calls the chat-completions endpoint and **falls back to the local
template engine** on any error, so the demo never breaks.

### 2. Azure AI Translator

```env
INSIDELENS_TRANSLATOR_PROVIDER=azure
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_KEY=...
AZURE_TRANSLATOR_REGION=...
```

`app/llm/translator.py::AzureTranslator` calls the Translator v3 REST API
(`/translate?api-version=3.0&to=…`) via `httpx`. It is preferred over the LLM for
translations; on any error it returns `None` and the caller falls back to the
Azure OpenAI client and then to the offline template engine. Used by
`engine/i18n.py` (per-insight translations) and `engine/personas.py` (recaps).

### 3. Azure SQL Database (persist insights)

```env
INSIDELENS_STORE_BACKEND=azuresql
AZURE_SQL_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=...
INSIDELENS_AZURE_SQL_TABLE=insidelens_insights
```

`app/store/repository.py::AzureSqlInsightRepository` lazily imports `pyodbc`,
auto-creates the table and upserts insights. Requires `pip install pyodbc`.

### 4. Microsoft Fabric / OneLake (analytics lakehouse)

```env
INSIDELENS_STORE_BACKEND=fabric
AZURE_STORAGE_CONNECTION_STRING=...
INSIDELENS_FABRIC_CONTAINER=insidelens
```

`FabricOneLakeRepository` uploads JSONL insight batches to a Fabric OneLake
(ADLS Gen2) container. The engine's expanded event dataset
(`store/dataset.py`) is what you load into a **Fabric Lakehouse** for downstream
ML/BI — the columns already contain engineered features (`zone`, `flank`,
`distance_to_goal`, `shot_angle`, `is_shot`, `is_on_target`, `is_goal`,
`pressure_score`).

```powershell
# Produce a Delta/Parquet-friendly export for the lakehouse
pip install pyarrow deltalake
curl "http://127.0.0.1:8000/api/dataset/export?format=delta"
curl "http://127.0.0.1:8000/api/dataset/export?format=parquet"
# Upload straight to the OneLake Fabric container
curl "http://127.0.0.1:8000/api/dataset/export?format=delta&upload=true"
```

`store/dataset.py::to_delta` writes a real Delta table via `deltalake` +
`pyarrow`; `to_parquet` writes Parquet. Both degrade gracefully (Delta → Parquet
→ JSONL) when the optional libraries are absent, so exports never fail on stage.
`FabricOneLakeRepository.upload_file` pushes the artefact into OneLake.

### 5. Real-time ingestion (Azure Event Hubs)

`app/data/sources.py` defines a pluggable `EventSource`:

- `SyntheticSource` — the deterministic simulator (default).
- `ReplaySource` — replays a recorded JSONL feed (`ReplaySource.from_jsonl`).
- `EventHubSource` — consumes a live Azure Event Hubs stream via
  `azure-eventhub` (lazy import), normalising each payload into a `MatchEvent`
  with `normalize_event`.

`MatchPipeline` consumes any source, so switching from simulation to live is a
config change:

```env
INSIDELENS_DATA_SOURCE=eventhub
AZURE_EVENTHUB_CONNECTION_STRING=Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...
AZURE_EVENTHUB_NAME=match-events
AZURE_EVENTHUB_CONSUMER_GROUP=$Default
```

When `realtime` sources are used the pipeline no longer simulates pacing — it
reacts to events as they arrive. You can also force a source per request:
`/ws/live?source=eventhub` or `?source=synthetic`.

## Suggested deployment topology

```
 Event Hubs  →  Azure Functions (normalise → MatchEvent)
                     │
                     ▼
             InsideLens FastAPI (Container Apps)
             ├── Foundry / Azure OpenAI   (narratives, recaps, personas)
             ├── Azure AI Translator      (multi-language)
             ├── Azure SQL                (insight persistence)
             └── Fabric OneLake           (analytics dataset / ML)
                     │
                     ▼
             Web dashboard (studios / streaming / fans)
```
