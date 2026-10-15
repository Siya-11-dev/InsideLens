from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INSIDELENS_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000

    llm_provider: Literal["local", "azure"] = "local"
    azure_openai_endpoint: str = Field("", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field("", validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field("gpt-4o", validation_alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field("2024-10-21", validation_alias="AZURE_OPENAI_API_VERSION")

    translator_provider: Literal["local", "azure"] = "local"
    azure_translator_endpoint: str = Field("", validation_alias="AZURE_TRANSLATOR_ENDPOINT")
    azure_translator_key: str = Field("", validation_alias="AZURE_TRANSLATOR_KEY")
    azure_translator_region: str = Field("", validation_alias="AZURE_TRANSLATOR_REGION")

    store_backend: Literal["memory", "azuresql", "fabric"] = "memory"
    azure_sql_connection: str = Field("", validation_alias="AZURE_SQL_CONNECTION_STRING")
    azure_sql_table: str = "insidelens_insights"
    fabric_connection: str = Field("", validation_alias="AZURE_STORAGE_CONNECTION_STRING")
    fabric_container: str = "insidelens"
    export_dir: str = "exports"

    data_source: Literal["synthetic", "eventhub"] = "synthetic"
    eventhub_connection: str = Field("", validation_alias="AZURE_EVENTHUB_CONNECTION_STRING")
    eventhub_name: str = Field("", validation_alias="AZURE_EVENTHUB_NAME")
    eventhub_consumer_group: str = Field("$Default", validation_alias="AZURE_EVENTHUB_CONSUMER_GROUP")

    match_seed: int = 20261015
    home_team: str = "MUN"
    away_team: str = "MCI"
    stream_speed: float = 60.0

    @property
    def azure_llm_ready(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def azure_translator_ready(self) -> bool:
        return bool(self.azure_translator_endpoint and self.azure_translator_key)

    @property
    def eventhub_ready(self) -> bool:
        return bool(self.eventhub_connection and self.eventhub_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
