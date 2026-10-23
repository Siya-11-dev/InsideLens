from __future__ import annotations

from app.agents.base import Agent


class NarrativeAgent(Agent):
    name = "narrative-writer"
    role = "Writes broadcast-style recaps and stories"

    async def run(self, context, task):
        pipeline = context["pipeline"]
        persona_id = context.get("persona_id")
        text = await pipeline.recap(persona_id=persona_id)
        return {"agent": self.name, "recap": text}
