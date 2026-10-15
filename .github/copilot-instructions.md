# InsideLens — GitHub Copilot instructions

These instructions tell GitHub Copilot (chat, inline suggestions, and the coding agent)
how this repository is built, so generated code matches the existing style.

## What this project is
InsideLens turns a synthetic, football-realistic event stream into **explainable match
intelligence**: real-time tactical insights, auto-highlights and multilingual recaps. Every
insight must ship with three explainability pillars: weighted factors (sum to 1), an
evidence list citing concrete event ids, and a counterfactual.

## Stack
- Python 3.11+, async first.
- FastAPI + Uvicorn, WebSocket streaming, Pydantic v2 models.
- Pure-Python analytics engine (no heavy ML deps in the default install).
- Optional, lazy Azure/Fabric integrations (Event Hubs, Azure OpenAI, Azure Translator,
  Azure SQL, Fabric/OneLake). The app must always run with **zero cloud keys**.

## Layout
- `app/data/` — teams registry + deterministic simulator + event sources.
- `app/engine/` — metrics, analytics, patterns, highlights, explain, personas, narrative, i18n, pipeline.
- `app/llm/` — LLM + translator clients (local default, Azure adapters).
- `app/store/` — dataset export + insight repositories (memory / Azure SQL / Fabric).
- `app/static/` — vanilla JS dashboard (no build step).
- `tests/` — pytest suite.

## Conventions (please follow)
- No inline code comments unless they add real value; prefer clear names.
- Keep Azure imports **inside** methods and wrap them in try/except so the offline path
  never breaks. Never add a hard dependency on an Azure package in `requirements.txt`.
- New Azure behaviour goes behind the existing provider pattern (`factory.py` files) and
  must degrade gracefully to the local implementation.
- Models are Pydantic v2. Use `Field(default_factory=...)` for mutable defaults.
- Keep functions small and pure where possible; the engine should be deterministic given a seed.
- Public functions/classes get type hints.
- Match the ASCII-safe source style already used in the repo.

## Commands
- Run app: `python -m uvicorn app.main:app --reload --port 8000`
- Tests: `python -m pytest -q`
- Azure exercise: `python scripts/azure_smoke.py`
- On Windows set `PYTHONUTF8=1` before running.

## Testing expectations
- Add or update tests for any behaviour change.
- Simulator/analytics tests are seeded and deterministic — never assert hard-coded scorelines
  or event counts that depend on RNG tuning; assert structural/behavioural properties instead.
- Azure integration tests must skip cleanly when credentials are absent.

## Do not
- Do not commit secrets, `.env`, `exports/`, `__pycache__/` or `.venv/`.
- Do not introduce a frontend build tool or framework; keep the dashboard dependency-free.
