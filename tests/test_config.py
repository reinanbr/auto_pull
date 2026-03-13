"""tests/test_config.py - Unit tests for AutoPull config loading and validation."""

import json

import pytest

from autopull.config import ConfigError, load_config


def test_load_valid_config(tmp_path) -> None:
    """Load a valid configuration and apply defaults."""
    config = {
        "site": {
            "path": "/var/www/site",
            "secret": "plain-secret",
        }
    }
    cfg_path = tmp_path / "projects.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    loaded = load_config(str(cfg_path))

    assert loaded["site"]["path"] == "/var/www/site"
    assert loaded["site"]["branch"] == "main"
    assert loaded["site"]["compose_file"] == "docker-compose.yml"


def test_missing_required_field(tmp_path) -> None:
    """Raise error when required field is missing."""
    config = {
        "site": {
            "path": "/var/www/site",
        }
    }
    cfg_path = tmp_path / "projects.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg_path))

    assert "missing required field 'secret'" in str(exc.value)


def test_secret_env_substitution(tmp_path, monkeypatch) -> None:
    """Resolve ${ENV_VAR} syntax in secret values."""
    monkeypatch.setenv("TEST_WEBHOOK_SECRET", "resolved-secret")

    config = {
        "site": {
            "path": "/var/www/site",
            "secret": "${TEST_WEBHOOK_SECRET}",
            "branch": "main",
            "compose_file": "docker-compose.yml",
        }
    }
    cfg_path = tmp_path / "projects.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    loaded = load_config(str(cfg_path))

    assert loaded["site"]["secret"] == "resolved-secret"


def test_missing_secret_env_var(tmp_path) -> None:
    """Raise error when secret references missing environment variable."""
    config = {
        "site": {
            "path": "/var/www/site",
            "secret": "${MISSING_WEBHOOK_SECRET}",
        }
    }
    cfg_path = tmp_path / "projects.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg_path))

    assert "environment variable is not set" in str(exc.value)
