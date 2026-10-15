import asyncio

from app.engine.pipeline import MatchPipeline


def test_analyze_full_consistency():
    p = MatchPipeline(seed=20261015)
    result = p.analyze_full()
    home, away = (int(x) for x in result["score"].split("-"))
    assert home + away == len(result["goals"])
    assert result["patterns"]


def test_stream_emits_expected_frames():
    async def run():
        p = MatchPipeline(seed=7)
        kinds = []
        insights = []
        async for frame in p.stream(speed=1_000_000):
            kinds.append(frame["type"])
            if frame["type"] == "insight":
                insights.append(frame["insight"])
        return kinds, insights

    kinds, insights = asyncio.run(run())
    assert kinds[0] == "match_init"
    assert kinds[-1] == "end"
    assert kinds.count("tick") > 50
    assert insights
    sample = insights[0]
    assert "translations" in sample
    assert "narrative" in sample and sample["narrative"]


def test_every_insight_has_structured_explanation():
    async def run():
        p = MatchPipeline(seed=42)
        out = []
        async for frame in p.stream(speed=1_000_000):
            if frame["type"] == "insight":
                out.append(frame["insight"])
        return out

    for ins in asyncio.run(run()):
        assert ins["factors"]
        assert ins["evidence"]
        assert ins["confidence"] > 0
