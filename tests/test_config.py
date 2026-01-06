from __future__ import annotations

from pathlib import Path

from lattis.settings.storage import load_or_create_session_id, load_storage_config, resolve_storage_config


def test_resolve_storage_config_is_pure(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    workspace_dir = tmp_path / "workspace"

    config = resolve_storage_config(
        project_root=tmp_path,
        data_dir=data_dir,
        workspace_dir=workspace_dir,
    )

    assert config.data_dir == data_dir
    assert config.workspace_dir == workspace_dir
    assert not data_dir.exists()
    assert not workspace_dir.exists()


def test_load_storage_config_creates_dirs(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    workspace_dir = tmp_path / "workspace"

    config = load_storage_config(
        project_root=tmp_path,
        data_dir=data_dir,
        workspace_dir=workspace_dir,
    )

    assert config.data_dir.is_dir()
    assert config.workspace_dir.is_dir()


def test_load_or_create_session_id_creates_parent(tmp_path: Path) -> None:
    session_path = tmp_path / "nested" / "session_id"
    session_id = load_or_create_session_id(session_path)

    assert session_path.exists()
    assert session_id == session_path.read_text(encoding="utf-8").strip()
