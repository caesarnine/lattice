from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lattice.agents.registry import AgentRegistry
from lattice.config import StorageConfig
from lattice.core.session import SessionStore


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
