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
    workspace: Path
    project_root: Path
    registry: AgentRegistry
