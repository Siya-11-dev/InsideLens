from __future__ import annotations

from app.engine.personas import get_persona
from app.llm.factory import get_llm


def _context(pipeline) -> dict:
    result = pipeline.analyze_full()
    state = result["state"]
    home = state["home"]
    away = state["away"]
    goals = result["goals"]
    patterns = result["patterns"]
    highlights = result["highlights"]
    return {
        "match": result["match"]["home"]["name"] + " vs " + result["match"]["away"]["name"],
        "score": result["score"],
        "home": home,
        "away": away,
        "goals": [g.get("claim") for g in goals],
        "patterns": [p.get("title") for p in patterns[:6]],
        "highlights": [h.get("title") for h in highlights[:5]],
        "top_insights": [i.get("claim") for i in (goals + patterns)[:6]],
    }


_TOOLS = {
    "score": lambda ctx: f"Final score {ctx['score']}.",
    "xg": lambda ctx: f"xG: {ctx['home']['xg']} ({ctx['home']['shots']} shots) vs {ctx['away']['xg']} ({ctx['away']['shots']} shots).",
    "possession": lambda ctx: f"Possession {ctx['home']['possession']}% vs {ctx['away']['possession']}%; field tilt {ctx['home']['field_tilt']}% vs {ctx['away']['field_tilt']}%.",
    "patterns": lambda ctx: "Patterns: " + (", ".join(ctx["patterns"]) or "none"),
    "highlights": lambda ctx: "Highlights: " + (", ".join(ctx["highlights"]) or "none"),
    "insights": lambda ctx: "Key insights: " + (", ".join(ctx["top_insights"]) or "none"),
}


def _select_tools(question: str) -> list[str]:
    q = question.lower()
    selected = []
    if any(w in q for w in ("score", "result", "winner")):
        selected.append("score")
    if any(w in q for w in ("xg", "chance", "quality", "shot")):
        selected.append("xg")
    if any(w in q for w in ("possession", "control", "dominate")):
        selected.append("possession")
    if any(w in q for w in ("tactic", "pattern", "press", "block", "formation")):
        selected.append("patterns")
    if any(w in q for w in ("highlight", "moment", "best")):
        selected.append("highlights")
    if not selected:
        selected = ["score", "xg", "patterns", "insights"]
    if "insight" in q or "why" in q or "explain" in q:
        selected.append("insights")
    return list(dict.fromkeys(selected))


async def answer(pipeline, question: str, persona_id: str | None = None, llm=None) -> dict:
    llm = llm or get_llm()
    ctx = _context(pipeline)
    tool_results = [f"- {name}: {_TOOLS[name](ctx)}" for name in _select_tools(question)]
    system = (
        "You are InsideLens, an explainable football match analyst. "
        "Answer the user's question using only the provided match context and tool results. "
        "Be concise (2-4 sentences), cite evidence (xG, event ids when available), and include a counterfactual when relevant."
    )
    user = (
        f"Match: {ctx['match']}\n"
        + "\n".join(tool_results)
        + f"\nGoals: {ctx['goals']}\n"
        + f"Question: {question}"
    )
    text = await llm.compose(system, user)
    if not text:
        # deterministic fallback
        parts = [tool_results and tool_results[0].lstrip("- ")]
        if ctx["top_insights"]:
            parts.append(ctx["top_insights"][0])
        if ctx["goals"]:
            parts.append("Counterfactual: " + (pipeline.analyze_full()["goals"][0].get("counterfactual") or ""))
        text = " ".join(p for p in parts if p)
    persona = get_persona(persona_id) if persona_id else None
    if persona and persona.language != "en":
        translated = await llm.translate(text, persona.language)
        if translated:
            text = translated
    return {
        "question": question,
        "answer": text,
        "persona": persona.id if persona else None,
        "tools": _select_tools(question),
        "context": {
            "score": ctx["score"],
            "xg_home": ctx["home"]["xg"],
            "xg_away": ctx["away"]["xg"],
        },
    }
