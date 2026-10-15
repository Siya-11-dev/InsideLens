# Azure exercise

InsideLens runs fully offline with **no cloud keys**. Every Azure integration is optional,
lazy-imported, and falls back to a deterministic local implementation. This document is a
hands-on exercise that proves each Azure path end-to-end when credentials are available,
without changing the code.

## How it is wired

| Capability | Provider switch | Adapter | Offline fallback |
|---|---|---|---|
| LLM narratives | `INSIDELENS_LLM_PROVIDER=azure` | `app/llm/azure.py` (`AzureOpenAIClient`) | `app/llm/local.py` templates |
| Translation | `INSIDELENS_TRANSLATOR_PROVIDER=azure` | `app/llm/translator.py` (`AzureTranslator`) | returns `None` → English retained |
| Insight store | `INSIDELENS_STORE_BACKEND=azuresql` | `app/store/repository.py` (`AzureSqlInsightRepository`) | in-memory list |
| Fabric / OneLake export | `INSIDELENS_STORE_BACKEND=fabric` | `FabricOneLakeRepository` | local `exports/` folder |
| Live event feed | `INSIDELENS_DATA_SOURCE=eventhub` | `app/data/sources.py` (`EventHubSource`) | `SyntheticSource` / `ReplaySource` |

Provider selection lives in `app/llm/factory.py`, `app/llm/translator.py` (`get_translator`),
`app/store/factory.py` and `app/data/sources.py` (`get_source`). All read `app/config.py`.

## 1. Provoke the offline fallback (no keys)

```powershell
$env:PYTHONUTF8=1
python scripts/azure_smoke.py
```

Expected: every line reports `SKIP` and the exit code is `0`. The app behaves identically:

```powershell
python -m uvicorn app.main:app --reload --port 8000
# GET http://127.0.0.1:8000/api/health -> providers "local"/"memory"/"synthetic"
```

## 2. Provision the Azure resources

| Service | Suggested resource | You need |
|---|---|---|
| Azure OpenAI | an Azure OpenAI resource + a `gpt-4o` deployment | endpoint, key, deployment name |
| Azure AI Translator | a Translator resource | endpoint, key, region |
| Azure SQL | a SQL database | full ODBC connection string |
| Fabric / OneLake | a Fabric lakehouse or a Storage account container | storage connection string + container |
| Azure Event Hubs | an Event Hubs namespace + hub | connection string + hub name |

## 3. Configure

Copy `.env.example` to `.env` and fill the values you provisioned, or export them directly:

```powershell
$env:INSIDELENS_LLM_PROVIDER="azure"
$env:AZURE_OPENAI_ENDPOINT="https://<res>.openai.azure.com"
$env:AZURE_OPENAI_API_KEY="<key>"
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4o"

$env:INSIDELENS_TRANSLATOR_PROVIDER="azure"
$env:AZURE_TRANSLATOR_ENDPOINT="https://api.cognitive.microsofttranslator.com"
$env:AZURE_TRANSLATOR_KEY="<key>"
$env:AZURE_TRANSLATOR_REGION="westeurope"

$env:INSIDELENS_STORE_BACKEND="azuresql"          # or "fabric"
$env:AZURE_SQL_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=tcp:<srv>.database.windows.net,1433;Database=<db>;Uid=<user>;Pwd=<pwd>;Encrypt=yes;"
# or
$env:AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=<acct>;AccountKey=<key>;EndpointSuffix=core.windows.net"
$env:INSIDELENS_FABRIC_CONTAINER="insidelens"

$env:INSIDELENS_DATA_SOURCE="eventhub"
$env:AZURE_EVENTHUB_CONNECTION_STRING="Endpoint=sb://<ns>.servicebus.windows.net/;SharedAccessKeyName=<name>;SharedAccessKey=<key>"
$env:AZURE_EVENTHUB_NAME="insidelens-events"
```

Install the optional SDKs:

```powershell
python -m pip install -r requirements-azure.txt
```

## 4. Run the exercise

```powershell
$env:PYTHONUTF8=1
python scripts/azure_smoke.py
```

Each configured capability should report `PASS`:

```
  [   PASS   ] Azure OpenAI (narrative) - A high turnover 32m from goal created a 0.34 xG chance...
  [   PASS   ] Azure Translator - Una pérdida en el último tercio creó una ocasión de 0,34 xG...
  [   PASS   ] Azure SQL insights - upserted 1 insight(s) into 'insidelens_insights'
  [   PASS   ] Fabric / OneLake upload - smoke/insidelens_smoke.jsonl
  [   PASS   ] Azure Event Hubs - connected to 'insidelens-events' (2 partitions)
```

`FALLBACK` means the switch is on but the live call failed and the offline path was used —
check endpoint/key/region and network access.

## 5. Exercise through the live app

```powershell
python -m uvicorn app.main:app --reload --port 8000
# GET /api/health                              -> confirm "llm_ready": true, backend names
# GET /api/analysis?translate=true             -> Azure OpenAI narratives + translations in the insight body
# GET /api/dataset/export?format=delta&upload=true  -> writes the dataset to Fabric/OneLake
# WS  /ws/live?source=eventhub                 -> streams from Event Hubs instead of the simulator
```

## 6. Automated checks

- `tests/test_azure_integration.py` runs the same live calls but **skips automatically**
  when a capability is not configured, so `python -m pytest -q` stays green offline.
- `.github/workflows/azure-smoke.yml` runs `scripts/azure_smoke.py` on demand
  (`workflow_dispatch`) using repository secrets, after installing the ODBC driver.

## Definition of done for the exercise

- `python scripts/azure_smoke.py` reports `PASS` for every provisioned service.
- `python -m pytest -q` is green with zero Azure keys and with keys configured.
- `/api/health` reflects the enabled providers and repositories.
