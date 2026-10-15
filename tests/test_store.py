from app.store.repository import (
    AzureSqlInsightRepository,
    FabricOneLakeRepository,
    InMemoryInsightRepository,
)
from app.models import Insight


def _sample() -> list[Insight]:
    return [
        Insight(id="i1", kind="goal_explanation", minute=10, title="Goal", claim="c", confidence=0.8),
        Insight(id="i2", kind="tactical_pattern", minute=20, title="Press", claim="c", confidence=0.6),
    ]


def test_memory_repository_saves_and_counts():
    repo = InMemoryInsightRepository()
    saved = repo.save_many("M1", _sample())
    assert saved == 2
    assert repo.count() == 2
    assert repo.all()[0]["match_id"] == "M1"


def test_azure_sql_repository_degrades_gracefully():
    repo = AzureSqlInsightRepository("Driver={ODBC Driver 18 for SQL Server};", "t")
    saved = repo.save_many("M1", _sample())
    assert saved == 2
    assert repo.count() == 2


def test_fabric_repository_degrades_gracefully():
    repo = FabricOneLakeRepository("UseDevelopmentStorage=false;", "container")
    saved = repo.save_many("M1", _sample())
    assert saved == 2
    assert repo.count() == 2


def test_fabric_upload_file_degrades_gracefully(tmp_path):
    repo = FabricOneLakeRepository("UseDevelopmentStorage=false;", "container")
    target = tmp_path / "data.jsonl"
    target.write_text("{}\n", encoding="utf-8")
    assert repo.upload_file(str(target), "datasets/data.jsonl") is False
