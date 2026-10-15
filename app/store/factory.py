from __future__ import annotations

from app.config import get_settings
from app.store.repository import (
    AzureSqlInsightRepository,
    FabricOneLakeRepository,
    InMemoryInsightRepository,
    InsightRepository,
)

_repository: InsightRepository | None = None


def get_repository() -> InsightRepository:
    global _repository
    if _repository is not None:
        return _repository
    settings = get_settings()
    backend = settings.store_backend
    if backend == "azuresql" and settings.azure_sql_connection:
        _repository = AzureSqlInsightRepository(
            settings.azure_sql_connection, settings.azure_sql_table
        )
    elif backend == "fabric" and settings.fabric_connection:
        _repository = FabricOneLakeRepository(
            settings.fabric_connection, settings.fabric_container
        )
    else:
        _repository = InMemoryInsightRepository()
    return _repository
