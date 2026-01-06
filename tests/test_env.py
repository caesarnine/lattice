from __future__ import annotations

from lattis.settings.env import first_env, read_bool_env, read_env


def test_read_env_strips_and_ignores_blank(monkeypatch) -> None:
    monkeypatch.setenv("LATTIS_TEST_ENV", "   ")
    assert read_env("LATTIS_TEST_ENV") is None

    monkeypatch.setenv("LATTIS_TEST_ENV", " value ")
    assert read_env("LATTIS_TEST_ENV") == "value"


def test_first_env_returns_first_non_empty(monkeypatch) -> None:
    monkeypatch.delenv("LATTIS_ENV_A", raising=False)
    monkeypatch.setenv("LATTIS_ENV_B", "   ")
    monkeypatch.setenv("LATTIS_ENV_C", "final")

    assert first_env("LATTIS_ENV_A", "LATTIS_ENV_B", "LATTIS_ENV_C") == "final"


def test_read_bool_env_defaults_and_parses(monkeypatch) -> None:
    monkeypatch.delenv("LATTIS_BOOL_ENV", raising=False)
    assert read_bool_env("LATTIS_BOOL_ENV", default=True) is True

    monkeypatch.setenv("LATTIS_BOOL_ENV", "true")
    assert read_bool_env("LATTIS_BOOL_ENV") is True

    monkeypatch.setenv("LATTIS_BOOL_ENV", "0")
    assert read_bool_env("LATTIS_BOOL_ENV") is False
