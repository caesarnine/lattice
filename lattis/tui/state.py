from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentSelectionState:
    current_id: str | None = None
    current_name: str | None = None
    default_id: str | None = None
    cache: list[tuple[str, str]] | None = None
    loading: bool = False

    def label(self) -> str:
        return self.current_name or self.current_id or "(unknown)"


@dataclass
class ModelSelectionState:
    current: str | None = None
    default: str | None = None
    cache: list[str] | None = None
    loading: bool = False
