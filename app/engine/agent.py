from __future__ import annotations

from app.agents.coordinator import CoordinatorAgent
from app.engine.personas import get_persona


async def answer(pipeline, question: str, persona_id: str | None = None, llm=None) -> dict:
    coordinator = CoordinatorAgent()
    context = {
        "pipeline": pipeline,
        "persona_id": persona_id,
        "language": get_persona(persona_id).language if persona_id else "en",
    }
    result = await coordinator.run(context, question)
    return {
        "question": question,
        "answer": result["answer"],
        "persona": result["persona"],
        "agents": result["agents"],
        "language": result["language"],
        "tactical": result["tactical"],
        "data": result["data"],
    }
