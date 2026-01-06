from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

import httpx
from fastapi import FastAPI

from lattis.client.api import AgentClient
from lattis.agents.registry import AgentRegistry, load_registry
from lattis.server.app import create_app
from lattis.settings.storage import StorageConfig, load_storage_config


@dataclass(frozen=True)
class InProcessServer:
    app: FastAPI
    config: StorageConfig
    registry: AgentRegistry


def create_inprocess_client(
    *,
    project_root: Path,
    workspace_mode: Literal["central", "local"] = "local",
    agent_specs: Iterable[str] | None = None,
    default_agent: str | None = None,
) -> tuple[AgentClient, InProcessServer]:
    config = load_storage_config(project_root=project_root, workspace_mode=workspace_mode)
    registry = load_registry(plugin_specs=agent_specs, default_spec=default_agent)
    app = create_app(config, registry=registry)
    transport = httpx.ASGITransport(app=app)
    base_url = "http://lattis.inprocess"
    http_client = httpx.AsyncClient(base_url=base_url, transport=transport)
    return (
        AgentClient(base_url, client=http_client),
        InProcessServer(app=app, config=config, registry=registry),
    )
