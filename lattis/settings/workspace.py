from __future__ import annotations

from pathlib import Path

from lattis.settings.storage import resolve_storage_config_from_env


def get_default_workspace() -> Path:
    """Get the default workspace path."""
    config = resolve_storage_config_from_env()
    return config.workspace_dir


def get_default_project_root() -> Path:
    """Get the default project root."""
    config = resolve_storage_config_from_env()
    return config.project_root


def ensure_workspace(path: Path) -> Path:
    """Ensure workspace directory structure exists."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "bin").mkdir(exist_ok=True)
    (path / "data").mkdir(exist_ok=True)
    (path / "tmp").mkdir(exist_ok=True)
    return path
