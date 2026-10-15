# Contributing to InsideLens

This project was built for *Inside the Game: Developer Hackathon* with **GitHub** and
**GitHub Copilot** as first-class tools. This guide explains how to extend it quickly
with Copilot, and how to propose changes.

## Getting set up

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest
python -m pytest -q          # 39 tests should pass
uvicorn app.main:app --reload --port 8000
```

## How to use GitHub Copilot here

The codebase is intentionally modular so Copilot has strong local context. Tips:

1. **Open the whole repo** in VS Code so Copilot sees related files (`models.py`,
   `engine/`, `store/`) when you edit.
2. **Describe intent in a docstring** and let Copilot complete the body — the engines
   are small, single-purpose functions.
3. Use **Copilot Chat** with `#file:app/models.py` and `#file:app/engine/explain.py`
   when adding a new insight type, so the model reuses the existing schema.
4. For a new tactical pattern, add it in three places (search for an existing one to
   copy the shape):
   - detection rule in `app/engine/patterns.py`
   - evidence/factors in `app/engine/explain.py` (`explain_pattern`)
   - localized phrase in `app/engine/narrative.py` (`_PATTERN_PHRASE`)
5. Run `python -m pytest -q` after every change. Tests are the contract.

### Useful prompts

- "Add a new `Persona` for a radio commentator that is brief, hype-toned and German."
- "Add a `xT` (expected threat) column to `app/store/dataset.py` and cover it with a test."
- "Implement `AzureBlobEventRepository` mirroring `AzureSqlInsightRepository`."

## Conventions

- **No inline comments** unless genuinely necessary; prefer clear names.
- Keep modules framework-free where possible (engines are pure Python).
- Any cloud dependency must be **lazy and optional**, with a working local fallback.
  This guarantees the demo runs with zero credentials.
- Add a test for every new engine, endpoint or serializer.

## Commit & PR checklist

- [ ] `python -m pytest -q` is green
- [ ] New behaviour has tests
- [ ] No secrets committed (`.env` is gitignored; use `.env.example` for new keys)
- [ ] README / docs updated for new endpoints or config
- [ ] Screenshots or a short clip for UI changes
