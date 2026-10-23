from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    name: str = "agent"
    role: str = "assistant"

    @abstractmethod
    async def run(self, context: dict[str, Any], task: str) -> dict[str, Any]:
        ...
