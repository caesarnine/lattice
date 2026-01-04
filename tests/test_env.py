from __future__ import annotations

from lattice.settings.env import first_env, read_bool_env, read_env


def test_read_env_strips_and_ignores_blank(monkeypatch) -> None:
    monkeypatch.setenv("LATTICE_TEST_ENV", "   ")
    assert read_env("LATTICE_TEST_ENV") is None

    monkeypatch.setenv("LATTICE_TEST_ENV", " value ")
    assert read_env("LATTICE_TEST_ENV") == "value"


def test_first_env_returns_first_non_empty(monkeypatch) -> None:
    monkeypatch.delenv("LATTICE_ENV_A", raising=False)
    monkeypatch.setenv("LATTICE_ENV_B", "   ")
    monkeypatch.setenv("LATTICE_ENV_C", "final")

    assert first_env("LATTICE_ENV_A", "LATTICE_ENV_B", "LATTICE_ENV_C") == "final"


def test_read_bool_env_defaults_and_parses(monkeypatch) -> None:
    monkeypatch.delenv("LATTICE_BOOL_ENV", raising=False)
    assert read_bool_env("LATTICE_BOOL_ENV", default=True) is True

    monkeypatch.setenv("LATTICE_BOOL_ENV", "true")
    assert read_bool_env("LATTICE_BOOL_ENV") is True

    monkeypatch.setenv("LATTICE_BOOL_ENV", "0")
    assert read_bool_env("LATTICE_BOOL_ENV") is False
