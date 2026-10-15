# AGENTS.md

Guidance for AI coding agents (GitHub Copilot coding agent, and similar tools) working in
this repository. See also `.github/copilot-instructions.md`.

## Quick start
```powershell
# Windows PowerShell
$env:PYTHONUTF8=1
python -m uvicorn app.main:app --reload --port 8000   # http://127.0.0.1:8000
python -m pytest -q                                    # run the test suite
python scripts/azure_smoke.py                          # optional: exercise Azure integrations
```
On cmd use `set PYTHONUTF8=1`, or just double-click `start.bat`.

## Ground rules
1. **Offline first.** The demo must run with no Azure keys. Azure/Fabric code is optional,
   lazy-imported and always falls back to the deterministic local implementation.
2. **Determinism.** `MatchSimulator` is seeded (`INSIDELENS_MATCH_SEED`). Tests must not
   hard-code scorelines/counts that depend on RNG tuning; assert properties instead.
3. **Explainability is the product.** Any new insight must carry weighted factors, evidence
   with event ids, and a counterfactual.
4. **Style.** No inline comments unless valuable; type hints on public APIs; Pydantic v2.

## Where things live
| Task | File(s) |
|---|---|
| Add/adjust a club or squad | `app/data/teams.py` |
| Change match generation | `app/data/simulator.py` |
| Ingest a new data source | `app/data/sources.py` |
| Analytics / xG / zones | `app/engine/metrics.py`, `app/engine/analytics.py` |
| Tactical patterns | `app/engine/patterns.py` |
| Explanations / counterfactuals | `app/engine/explain.py` |
| Highlights / recaps / personas | `app/engine/highlights.py`, `app/engine/narrative.py`, `app/engine/personas.py` |
| Streaming orchestration | `app/engine/pipeline.py` |
| HTTP / WebSocket API | `app/main.py` |
| Dataset export | `app/store/dataset.py` |
| Azure integrations | `app/llm/*`, `app/store/repository.py`, `app/data/sources.py` |

## Definition of done
- `python -m pytest -q` is green.
- New behaviour is covered by a test.
- Azure paths still degrade gracefully with no credentials.
- README/docs updated if user-facing behaviour changed.
