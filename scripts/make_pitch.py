from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

W, H = 1280, 720
OUT = Path(__file__).resolve().parents[1] / "docs" / "pitch.pdf"

NAVY = HexColor("#0a0f1c")
PANEL = HexColor("#111a2e")
ACCENT = HexColor("#22d3ee")
TEXT = HexColor("#e8eefc")
MUTED = HexColor("#8ea0c4")
GOOD = HexColor("#34d399")


def slide(c: canvas.Canvas, title: str | None = None, eyebrow: str | None = None) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # accent bar
    c.setFillColor(ACCENT)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    if eyebrow:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(80, H - 70, eyebrow.upper())
    if title:
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 44)
        c.drawString(80, H - 120, title)
    # footer
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 12)
    c.drawString(80, 40, "InsideLens  |  Explainable real-time match intelligence")
    c.drawRightString(W - 80, 40, "Microsoft x Premier League  |  Inside the Game Hackathon")


def bullets(c: canvas.Canvas, items: list[str], y_start: int, size: int = 24, color=TEXT, indent: int = 80) -> None:
    y = y_start
    for it in items:
        c.setFillColor(ACCENT)
        c.circle(indent + 6, y + 8, 4, fill=1, stroke=0)
        c.setFillColor(color)
        c.setFont("Helvetica", size)
        # wrap
        words = it.split()
        line = ""
        lines: list[str] = []
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, "Helvetica", size) > W - indent - 120:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        for ln in lines:
            c.drawString(indent + 24, y, ln)
            y -= size + 6
        y -= 6
    return


def center_text(c: canvas.Canvas, text: str, y: int, size: int = 28, color=TEXT, bold: bool = False) -> None:
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawCentredString(W / 2, y, text)


def make() -> None:
    c = canvas.Canvas(str(OUT), pagesize=(W, H))
    c.setTitle("InsideLens — Pitch")

    # Slide 1 title
    slide(c)
    center_text(c, "InsideLens", H / 2 + 60, size=72, color=ACCENT, bold=True)
    center_text(c, "Explainable real-time match intelligence for football", H / 2, size=26)
    center_text(c, "Turn synthetic football events into insights that show their work", H / 2 - 40, size=20, color=MUTED)
    center_text(c, "GitHub  |  Azure OpenAI  |  Translator  |  SQL  |  Fabric  |  Event Hubs", H / 2 - 100, size=16, color=MUTED)
    c.showPage()

    # Slide 2 problem
    slide(c, "The problem", "01  Problem")
    bullets(c, [
        "Match tools tell you WHAT happened (score, xG, possession) — never WHY.",
        "Models are black boxes: no evidence, no accountability.",
        "One feed for everyone ignores analysts, commentators, and fans.",
        "No audit trail for studios, streamers, or regulators.",
    ], H - 170)
    c.showPage()

    # Slide 3 solution
    slide(c, "Our solution", "02  Solution")
    bullets(c, [
        "InsideLens ingests a live event stream and explains every key moment in real time.",
        "Every insight ships with 3 explainability pillars: weighted factors, evidence graph, counterfactual.",
        "Detects tactical patterns: high press, low block, transitions, overloads, sustained pressure, set plays.",
        "Builds an explainable highlight reel ranked by an excitement score.",
        "Writes full-time recaps, localized to 6 languages and personalized to 7 personas.",
    ], H - 170)
    c.showPage()

    # Slide 4 demo
    slide(c, "Live demo", "03  Demo")
    bullets(c, [
        "Pick any 2 of 20 Premier League clubs (2026/27 squads). Default: Man Utd vs Man City.",
        "22 players move with the ball; fading trail; action arrows; goal celebrations.",
        "Streaming WebSocket: match_init -> tick -> insight -> end.",
        "Expand an insight card: factors (sum to 1), evidence (event ids), counterfactual, translations.",
        "Switch language and persona live; watch the recap rewrite.",
    ], H - 170)
    c.showPage()

    # Slide 5 explainability
    slide(c, "Explainability pillars", "04  Why it's different")
    bullets(c, [
        "1. Weighted factors — normalised contributions that sum to 1.",
        "2. Evidence graph — human-readable items citing exact event ids and metric deltas.",
        "3. Counterfactual — the single change that would most alter the outcome.",
        "Attached to EVERY insight, not just goals. 12/12 fully explained in eval.",
        "Confidence score + model provenance on each card.",
    ], H - 170)
    c.showPage()

    # Slide 6 capabilities mapped
    slide(c, "Mapped to the brief", "05  Capabilities")
    bullets(c, [
        "Analyze match events in real time — async streaming pipeline over WebSocket.",
        "Generate stories, highlights, recaps — highlights.py, narrative.py.",
        "Explain key moments & tactical patterns — explain.py, patterns.py.",
        "Expand datasets for AI/analytics — 28 engineered features, JSONL/CSV/Parquet/Delta.",
        "Multiple languages — EN/ES/FR/PT/AR/ZU, online or offline.",
        "Personalized experiences — 7 personas for fans, studios, broadcasters.",
    ], H - 170)
    c.showPage()

    # Slide 7 architecture
    slide(c, "Architecture & Azure", "06  Stack")
    bullets(c, [
        "Live feed: Synthetic / Replay / Azure Event Hubs (pluggable, lazy).",
        "Analytics: possession, xG, momentum, field tilt, press intensity, flanks.",
        "Narratives: Azure OpenAI on Microsoft Foundry (local template fallback).",
        "Translation: Azure AI Translator (offline template fallback).",
        "Persistence: Azure SQL Database; analytics lakehouse: Microsoft Fabric / OneLake.",
        "Runs with ZERO cloud keys; any Azure failure auto-falls back. Demo never breaks.",
    ], H - 170)
    c.showPage()

    # Slide 8 dataset
    slide(c, "Dataset expansion", "07  Data")
    bullets(c, [
        "28-column ML-ready export: zone, flank, distance-to-goal, shot angle, pressure score.",
        "Formats: JSONL, CSV, Parquet, Delta (deltalake + pyarrow).",
        "Upload straight to Fabric OneLake with upload=true.",
        "Synthetic, football-realistic data only — no real Premier League match data.",
        "Eval harness: 12 insights, 100% explained, factor sums = 1.0.",
    ], H - 170)
    c.showPage()

    # Slide 9 personalization
    slide(c, "Personalization & multilingual", "08  Reach")
    bullets(c, [
        "7 personas: studio-analyst, global-fan-es/fr/pt/ar, fan-home, fan-away.",
        "Tone, depth, stat-bias, favourite team, language per persona.",
        "Per-insight language chips; recap rewrites per persona.",
        "Conversational analyst endpoint /api/agent — tool-grounded, multilingual.",
        "Spatial viz: heatmaps, pass networks, expected threat (xT).",
    ], H - 170)
    c.showPage()

    # Slide 10 metrics
    slide(c, "Proof", "09  Quality")
    bullets(c, [
        "78 tests passing, 5 skipped offline; CI on Python 3.11 & 3.12.",
        "Azure smoke exercise reports PASS / FALLBACK / SKIP per provider.",
        "Deterministic seeded simulator (INSIDELENS_MATCH_SEED) — reproducible demos.",
        "Lazy Azure imports — no hard dependency in requirements.txt.",
        "GitHub Copilot instructions + AGENTS.md for AI-assisted development.",
    ], H - 170)
    c.showPage()

    # Slide 11 roadmap
    slide(c, "Roadmap & ask", "10  Next")
    bullets(c, [
        "Host on Azure Container Apps; live demo URL for judges.",
        "Add autonomous Foundry agent with tool-calling over match state.",
        "Voice commentary + live broadcast graphics overlay.",
        "Pilot with a studio: real-time insight feed into production.",
        "Ask: feedback on explainability UX and Azure deployment topology.",
    ], H - 170)
    c.showPage()

    # Slide 12 contact
    slide(c, "Thank you", "11  Contact")
    center_text(c, "InsideLens", H / 2 + 40, size=56, color=ACCENT, bold=True)
    center_text(c, "github.com/Siya-11-dev/InsideLens", H / 2 - 10, size=22)
    center_text(c, "Explainable real-time match intelligence  |  Azure-ready, offline-first", H / 2 - 50, size=18, color=MUTED)
    c.showPage()

    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    make()
