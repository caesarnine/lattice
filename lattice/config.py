from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class StorageConfig:
    data_dir: Path
    db_path: Path
    session_id_path: Path
    workspace_dir: Path
    project_root: Path
    workspace_mode: Literal["central", "local"]


def _coerce_path(value: Path | str) -> Path:
    return Path(value).expanduser()


def _resolve_workspace_mode(explicit: str | None) -> Literal["central", "local"]:
    value = (explicit or os.getenv("LATTICE_WORKSPACE_MODE") or "local").strip().lower()
    if value in {"local", "project", "cwd"}:
        return "local"
    return "central"


def _resolve_path_override(explicit: Path | None, env_var: str) -> Path | None:
    if explicit is not None:
        return _coerce_path(explicit)
    override = os.getenv(env_var)
    if override:
        return _coerce_path(override.strip())
    return None


def resolve_storage_config(
    *,
    project_root: Path | None = None,
    workspace_mode: str | None = None,
    data_dir: Path | None = None,
    workspace_dir: Path | None = None,
) -> StorageConfig:
    env_project_root = os.getenv("LATTICE_PROJECT_ROOT")
    if project_root is not None:
        resolved_project_root = _coerce_path(project_root)
    elif env_project_root:
        resolved_project_root = _coerce_path(env_project_root)
    else:
        resolved_project_root = Path.cwd()
    resolved_mode = _resolve_workspace_mode(workspace_mode)

    data_dir = _resolve_path_override(data_dir, "LATTICE_DATA_DIR")

    if data_dir is None:
        if resolved_mode == "local":
            data_dir = resolved_project_root / ".lattice"
        else:
            data_dir = Path.home() / ".lattice"

    workspace_dir = _resolve_path_override(workspace_dir, "LATTICE_WORKSPACE_DIR")

    if workspace_dir is None:
        workspace_dir = data_dir / "workspace"

    db_path_env = os.getenv("LATTICE_DB_PATH")
    db_path = _coerce_path(db_path_env) if db_path_env else data_dir / "lattice.db"
    session_path_env = os.getenv("LATTICE_SESSION_FILE")
    session_id_path = _coerce_path(session_path_env) if session_path_env else data_dir / "session_id"

    return StorageConfig(
        data_dir=data_dir,
        db_path=db_path,
        session_id_path=session_id_path,
        workspace_dir=workspace_dir,
        project_root=resolved_project_root,
        workspace_mode=resolved_mode,
    )


def ensure_storage_dirs(config: StorageConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.workspace_dir.mkdir(parents=True, exist_ok=True)


def load_storage_config(
    *,
    project_root: Path | None = None,
    workspace_mode: str | None = None,
    data_dir: Path | None = None,
    workspace_dir: Path | None = None,
) -> StorageConfig:
    config = resolve_storage_config(
        project_root=project_root,
        workspace_mode=workspace_mode,
        data_dir=data_dir,
        workspace_dir=workspace_dir,
    )
    ensure_storage_dirs(config)
    return config


def load_or_create_session_id(path: Path, *, env_var: str = "LATTICE_SESSION_ID") -> str:
    override = os.getenv(env_var)
    if override:
        return override
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    session_id = f"tui-{uuid.uuid4()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session_id, encoding="utf-8")
    return session_id
