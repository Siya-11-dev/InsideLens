from __future__ import annotations

from app.agents.base import Agent


class TacticalAnalystAgent(Agent):
    name = "tactical-analyst"
    role = "Analyzes match state, patterns, xG and expected threat"

    async def run(self, context, task):
        pipeline = context["pipeline"]
        result = pipeline.analyze_full()
        xt = pipeline.expected_threat()
        pn = pipeline.pass_network()
        return {
            "agent": self.name,
            "summary": {
                "score": result["score"],
                "patterns": [p.get("title") for p in result["patterns"][:6]],
                "goals": [g.get("claim") for g in result["goals"]],
                "xg_home": result["state"]["home"]["xg"],
                "xg_away": result["state"]["away"]["xg"],
                "xt_home": xt["home"],
                "xt_away": xt["away"],
                "pass_nodes": len(pn["nodes"]),
                "pass_edges": len(pn["edges"]),
            },
            "insights": result["goals"] + result["patterns"],
        }
