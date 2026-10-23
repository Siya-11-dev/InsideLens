from __future__ import annotations

import os
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import get_settings
from app.data.sources import get_source
from app.data.teams import list_clubs
from app.engine.narrative import LANGUAGES
from app.engine.personas import get_persona, list_personas
from app.engine.agent import answer as agent_answer
from app.engine.pipeline import MatchPipeline
from app.store.factory import get_repository

STATIC_DIR = Path(__file__).parent / "static"


def _pipeline(
    seed: int | None = None,
    source: str | None = None,
    home: str | None = None,
    away: str | None = None,
) -> MatchPipeline:
    if source == "eventhub":
        return MatchPipeline(source=get_source(get_settings(), seed, home_club=home, away_club=away))
    return MatchPipeline(seed=seed, home_team=home, away_team=away)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("INSIDELENS_OPEN_BROWSER", "1") == "1":
        def _open() -> None:
            time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{get_settings().port}")

        threading.Thread(target=_open, daemon=True).start()
    yield


app = FastAPI(
    title="InsideLens",
    description="Explainable real-time tactical intelligence for football.",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "llm_provider": settings.llm_provider,
        "llm_ready": settings.azure_llm_ready,
        "translator": settings.translator_provider,
        "translator_ready": settings.azure_translator_ready,
        "store": get_repository().name,
        "data_source": settings.data_source,
        "eventhub_ready": settings.eventhub_ready,
        "languages": LANGUAGES,
    }


@app.get("/api/personas")
async def personas() -> JSONResponse:
    return JSONResponse({"personas": [p.model_dump() for p in list_personas()]})


@app.get("/api/teams")
async def teams() -> JSONResponse:
    return JSONResponse({"teams": list_clubs()})


@app.get("/api/analysis")
async def analysis(
    seed: int | None = Query(default=None),
    translate: bool = Query(default=False),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    result = pipeline.analyze_full()
    if translate:
        from app.engine.i18n import localize
        from app.llm.factory import get_llm

        llm = get_llm()
        for group in ("goals", "patterns"):
            from app.models import Insight

            result[group] = [
                (await localize(Insight(**i), llm)).model_dump() for i in result[group]
            ]
    return JSONResponse(result)


@app.get("/api/recap")
async def recap(
    seed: int | None = Query(default=None),
    persona: str | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    text = await pipeline.recap(persona_id=persona)
    return JSONResponse({"recap": text, "persona": get_persona(persona).id if persona else None})


@app.get("/api/highlights")
async def highlights(
    seed: int | None = Query(default=None),
    persona: str | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse({"highlights": pipeline.highlights(persona_id=persona)})


@app.get("/api/personalize")
async def personalize(
    seed: int | None = Query(default=None),
    persona: str = Query(default="studio-analyst"),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse(
        {
            "persona": get_persona(persona).model_dump(),
            "insights": pipeline.personalized_insights(persona),
        }
    )


@app.get("/api/agents")
async def agents() -> JSONResponse:
    from app.agents import CoordinatorAgent

    coord = CoordinatorAgent()
    return JSONResponse(
        {
            "coordinator": coord.name,
            "agents": [
                {"name": a.name, "role": a.role}
                for a in (coord.tactical, coord.narrative, coord.localization, coord.data)
            ],
        }
    )


@app.get("/api/agent")
async def agent(
    seed: int | None = Query(default=None),
    question: str = Query(default="Why did the home team win?"),
    persona: str | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    result = await agent_answer(pipeline, question, persona_id=persona)
    return JSONResponse(result)


@app.get("/api/dataset/export")
async def dataset_export(
    seed: int | None = Query(default=None),
    format: str = Query(default="jsonl"),
    upload: bool = Query(default=False),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse(pipeline.export(fmt=format, upload=upload))


@app.get("/api/heatmap")
async def heatmap(
    seed: int | None = Query(default=None),
    team: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse(pipeline.heatmap(team_id=team, kind=kind))


@app.get("/api/pass-network")
async def pass_network(
    seed: int | None = Query(default=None),
    team: str | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse(pipeline.pass_network(team_id=team))


@app.get("/api/xt")
async def expected_threat(
    seed: int | None = Query(default=None),
    home: str | None = Query(default=None),
    away: str | None = Query(default=None),
) -> JSONResponse:
    pipeline = _pipeline(seed, home=home, away=away)
    return JSONResponse(pipeline.expected_threat())


@app.get("/api/store/stats")
async def store_stats() -> JSONResponse:
    repo = get_repository()
    return JSONResponse({"backend": repo.name, "insights": repo.count()})


@app.websocket("/ws/live")
async def live(websocket: WebSocket) -> None:
    await websocket.accept()
    seed = websocket.query_params.get("seed")
    speed = websocket.query_params.get("speed")
    persona = websocket.query_params.get("persona")
    source = websocket.query_params.get("source")
    home = websocket.query_params.get("home")
    away = websocket.query_params.get("away")
    try:
        pipeline = _pipeline(
            seed=int(seed) if seed else None,
            source=source,
            home=home,
            away=away,
        )
        await websocket.send_json(
            {
                "type": "status",
                "message": f"preparing {type(pipeline.source).__name__} feed...",
            }
        )
        async for frame in pipeline.stream(
            speed=float(speed) if speed else None,
            persona_id=persona or None,
        ):
            await websocket.send_json(frame)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # pragma: no cover
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
