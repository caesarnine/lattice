from __future__ import annotations

import os

LATTICE_SERVER_URL = "LATTICE_SERVER_URL"
LATTICE_WORKSPACE_MODE = "LATTICE_WORKSPACE_MODE"
LATTICE_PROJECT_ROOT = "LATTICE_PROJECT_ROOT"
LATTICE_DATA_DIR = "LATTICE_DATA_DIR"
LATTICE_WORKSPACE_DIR = "LATTICE_WORKSPACE_DIR"
LATTICE_DB_PATH = "LATTICE_DB_PATH"
LATTICE_SESSION_FILE = "LATTICE_SESSION_FILE"
LATTICE_SESSION_ID = "LATTICE_SESSION_ID"
LATTICE_MODEL = "LATTICE_MODEL"
LATTICE_LOGFIRE = "LATTICE_LOGFIRE"
LATTICE_GLOBAL_BIN = "LATTICE_GLOBAL_BIN"

AGENT_MODEL = "AGENT_MODEL"
AGENT_DEFAULT = "AGENT_DEFAULT"
AGENT_PLUGINS = "AGENT_PLUGINS"
AGENT_PLUGIN = "AGENT_PLUGIN"


def read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def first_env(*names: str) -> str | None:
    for name in names:
        value = read_env(name)
        if value is not None:
            return value
    return None


def read_bool_env(name: str, *, default: bool = False) -> bool:
    value = read_env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
