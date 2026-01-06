from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lattis.agents.registry import AgentRegistry
from lattis.domain.sessions import SessionStore
from lattis.settings.storage import StorageConfig


@dataclass(frozen=True)
class AppContext:
    config: StorageConfig
    store: SessionStore
    registry: AgentRegistry

    @property
    def workspace(self) -> Path:
        return self.config.workspace_dir

    @property
    def project_root(self) -> Path:
        return self.config.project_root
