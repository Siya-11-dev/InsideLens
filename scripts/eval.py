"""Offline evaluation harness for InsideLens.

Run: python scripts/eval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.pipeline import MatchPipeline


def main() -> None:
    p = MatchPipeline(seed=20261015)
    result = p.analyze_full()
    insights = result["goals"] + result["patterns"]
    factor_sums = [sum(f["weight"] for f in i["factors"]) for i in insights if i["factors"]]
    explained = sum(1 for i in insights if i["factors"] and i["evidence"] and i["counterfactual"])
    print("match:", result["match"]["home"]["name"], "vs", result["match"]["away"]["name"])
    print("score:", result["score"])
    print("insights:", len(insights))
    print("fully_explained:", explained, "/", len(insights))
    print("avg_factor_sum:", round(sum(factor_sums) / max(1, len(factor_sums)), 3))
    print("avg_evidence:", round(sum(len(i["evidence"]) for i in insights) / max(1, len(insights)), 2))
    print("highlights:", len(result["highlights"]))
    print("patterns:", len(result["patterns"]))
    xt = p.expected_threat()
    print("xT home/away:", xt["home"], xt["away"])
    pn = p.pass_network()
    print("pass_network nodes/edges:", len(pn["nodes"]), len(pn["edges"]))


if __name__ == "__main__":
    main()
