from __future__ import annotations

from app.agents.base import Agent


class DataEngineerAgent(Agent):
    name = "data-engineer"
    role = "Prepares expanded analytics dataset exports"

    async def run(self, context, task):
        pipeline = context["pipeline"]
        info = pipeline.export(fmt=context.get("format", "jsonl"), upload=False)
        return {"agent": self.name, "export": info}
