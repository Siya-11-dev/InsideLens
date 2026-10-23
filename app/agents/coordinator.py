from __future__ import annotations

from app.agents.base import Agent
from app.agents.tactical import TacticalAnalystAgent
from app.agents.narrative import NarrativeAgent
from app.agents.localization import LocalizationAgent
from app.agents.data import DataEngineerAgent
from app.engine.personas import get_persona


class CoordinatorAgent(Agent):
    name = "coordinator"
    role = "Orchestrates specialized agents based on the request"

    def __init__(self) -> None:
        self.tactical = TacticalAnalystAgent()
        self.narrative = NarrativeAgent()
        self.localization = LocalizationAgent()
        self.data = DataEngineerAgent()

    async def run(self, context, task):
        pipeline = context["pipeline"]
        persona = get_persona(context.get("persona_id")) if context.get("persona_id") else None
        lang = persona.language if persona else (context.get("language") or "en")
        question = task or ""

        trace: list[str] = []
        tactical_out = await self.tactical.run(context, question)
        trace.append(self.tactical.name)

        needs_story = any(w in question.lower() for w in ("recap", "story", "summary", "narrative"))
        needs_data = any(w in question.lower() for w in ("dataset", "export", "data", "features"))

        story_text = None
        if needs_story:
            nar = await self.narrative.run(context, question)
            story_text = nar["recap"]
            trace.append(self.narrative.name)

        # Build answer via tactical summary + insights
        summary = tactical_out["summary"]
        insights = tactical_out["insights"]
        top_claims = [i.get("claim") for i in insights[:4]]
        answer_parts = [
            f"{summary['score']} (xG {summary['xg_home']} vs {summary['xg_away']}, xT {summary['xt_home']} vs {summary['xt_away']}).",
        ]
        if summary["patterns"]:
            answer_parts.append("Patterns: " + ", ".join(summary["patterns"]) + ".")
        if top_claims:
            answer_parts.append("Key insights: " + " ".join(top_claims[:2]))
        if story_text:
            answer_parts.append("Recap: " + story_text)
        answer = " ".join(answer_parts)

        # localization
        loc = await self.localization.run({"text": answer, "language": lang}, question)
        trace.append(self.localization.name)
        answer = loc["text"]

        data_out = None
        if needs_data:
            data_out = await self.data.run(context, question)
            trace.append(self.data.name)

        return {
            "agent": self.name,
            "answer": answer,
            "language": lang,
            "persona": persona.id if persona else None,
            "agents": trace,
            "tactical": summary,
            "data": data_out,
        }
