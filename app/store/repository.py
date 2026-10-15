from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.models import Insight


class InsightRepository(ABC):
    name: str = "memory"

    @abstractmethod
    def save_many(self, match_id: str, insights: list[Insight]) -> int:
        ...

    @abstractmethod
    def all(self) -> list[dict]:
        ...

    def count(self) -> int:
        return len(self.all())


class InMemoryInsightRepository(InsightRepository):
    name = "memory"

    def __init__(self) -> None:
        self._rows: list[dict] = []

    def save_many(self, match_id: str, insights: list[Insight]) -> int:
        for ins in insights:
            row = ins.model_dump()
            row["match_id"] = match_id
            row["saved_at"] = datetime.now(timezone.utc).isoformat()
            self._rows.append(row)
        return len(insights)

    def all(self) -> list[dict]:
        return list(self._rows)


class AzureSqlInsightRepository(InsightRepository):
    """Persists insights to Azure SQL Database via pyodbc (lazy dependency)."""

    name = "azure-sql"

    def __init__(self, connection_string: str, table: str = "insidelens_insights") -> None:
        self.connection_string = connection_string
        self.table = table
        self._fallback = InMemoryInsightRepository()
        self._available = False
        try:
            import pyodbc  # noqa: F401

            self._available = True
        except Exception:
            self._available = False

    def _ensure_schema(self, cursor) -> None:
        cursor.execute(
            f"IF OBJECT_ID('{self.table}', 'U') IS NULL "
            f"CREATE TABLE {self.table} ("
            "id NVARCHAR(128) PRIMARY KEY, match_id NVARCHAR(64), "
            "kind NVARCHAR(64), minute INT, team_id NVARCHAR(16), "
            "title NVARCHAR(512), confidence FLOAT, payload NVARCHAR(MAX), "
            "saved_at DATETIME2 DEFAULT SYSUTCDATETIME())"
        )

    def save_many(self, match_id: str, insights: list[Insight]) -> int:
        if not self._available:
            return self._fallback.save_many(match_id, insights)
        import pyodbc

        conn = pyodbc.connect(self.connection_string)
        try:
            cur = conn.cursor()
            self._ensure_schema(cur)
            for ins in insights:
                cur.execute(
                    f"MERGE {self.table} AS t USING (SELECT ? AS id) AS s ON t.id = s.id "
                    "WHEN MATCHED THEN UPDATE SET payload=? "
                    "WHEN NOT MATCHED THEN INSERT (id, match_id, kind, minute, team_id, title, confidence, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    ins.id,
                    json.dumps(ins.model_dump(), ensure_ascii=False),
                    ins.id,
                    match_id,
                    ins.kind,
                    ins.minute,
                    ins.team_id,
                    ins.title,
                    ins.confidence,
                    json.dumps(ins.model_dump(), ensure_ascii=False),
                )
            conn.commit()
        finally:
            conn.close()
        return len(insights)

    def all(self) -> list[dict]:
        return self._fallback.all()


class FabricOneLakeRepository(InsightRepository):
    """Writes insight batches to a Fabric OneLake (ADLS Gen2) / blob container."""

    name = "fabric-onelake"

    def __init__(self, connection_string: str, container: str) -> None:
        self.connection_string = connection_string
        self.container = container
        self._fallback = InMemoryInsightRepository()
        self._available = False
        try:
            import azure.storage.blob  # noqa: F401

            self._available = True
        except Exception:
            self._available = False

    def save_many(self, match_id: str, insights: list[Insight]) -> int:
        self._fallback.save_many(match_id, insights)
        if not self._available:
            return len(insights)
        from azure.storage.blob import BlobServiceClient

        rows = self._fallback.all()
        payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        client = BlobServiceClient.from_connection_string(self.connection_string)
        name = f"insights/{match_id}/insights_{datetime.now(timezone.utc):%Y%m%d%H%M%S}.jsonl"
        blob = client.get_blob_client(container=self.container, blob=name)
        blob.upload_blob(payload, overwrite=True)
        return len(insights)

    def upload_file(self, local_path: str, remote_name: str) -> bool:
        if not self._available:
            return False
        from azure.storage.blob import BlobServiceClient

        client = BlobServiceClient.from_connection_string(self.connection_string)
        blob = client.get_blob_client(container=self.container, blob=remote_name)
        with open(local_path, "rb") as fh:
            blob.upload_blob(fh, overwrite=True)
        return True

    def all(self) -> list[dict]:
        return self._fallback.all()
