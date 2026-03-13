#!/usr/bin/env python3
"""autopull/config.py - Configuration loader and validator for AutoPull."""

import json
import os
import re
from typing import Any, Dict

DEFAULT_CONFIG_PATH = "/etc/autopull/projects.json"
_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


class ConfigError(Exception):
    """Raised when the AutoPull configuration is invalid."""


def _resolve_secret(secret_value: str, project_name: str) -> str:
    """Resolve ${ENV_VAR} secrets and return a concrete secret value."""
    match = _ENV_PATTERN.match(secret_value)
    if not match:
        return secret_value

    env_var = match.group(1)
    resolved = os.environ.get(env_var)
    if not resolved:
        raise ConfigError(
            f"Project '{project_name}' secret uses '{env_var}', but that "
            "environment variable is not set."
        )
    return resolved


def _require_string(data: Dict[str, Any], key: str, project_name: str) -> str:
    """Read a required string key from project data."""
    value = data.get(key)
    if value is None:
        raise ConfigError(
            f"Project '{project_name}' is missing required field '{key}'."
        )
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            f"Project '{project_name}' field '{key}' must be "
            "a non-empty string."
        )
    return value.strip()


def _optional_string(
    data: Dict[str, Any], key: str, default: str, project_name: str
) -> str:
    """Read an optional string key from project data, applying a default."""
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            f"Project '{project_name}' field '{key}' must be "
            "a non-empty string."
        )
    return value.strip()


def _validate_project(
    name: str, project_data: Dict[str, Any]
) -> Dict[str, str]:
    """Validate and normalize a single project configuration."""
    if not isinstance(project_data, dict):
        raise ConfigError(f"Project '{name}' must be a JSON object.")

    path = _require_string(project_data, "path", name)
    secret = _resolve_secret(
        _require_string(project_data, "secret", name), name
    )
    branch = _optional_string(project_data, "branch", "main", name)
    compose_file = _optional_string(
        project_data, "compose_file", "docker-compose.yml", name
    )

    return {
        "path": path,
        "secret": secret,
        "branch": branch,
        "compose_file": compose_file,
    }


def load_config(config_path: str | None = None) -> Dict[str, Dict[str, str]]:
    """Load and validate AutoPull project configuration from disk."""
    path = config_path or os.environ.get(
        "AUTOPULL_CONFIG", DEFAULT_CONFIG_PATH
    )

    if not os.path.exists(path):
        raise ConfigError(
            f"Configuration file not found at '{path}'. "
            "Set AUTOPULL_CONFIG or create the file."
        )

    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Configuration file '{path}' contains invalid JSON: {exc}"
        )
    except OSError as exc:
        raise ConfigError(f"Unable to read configuration file '{path}': {exc}")

    if not isinstance(raw_data, dict):
        raise ConfigError(
            "Configuration root must be a JSON object keyed by project name."
        )
    if not raw_data:
        raise ConfigError("Configuration file does not define any projects.")

    normalized: Dict[str, Dict[str, str]] = {}
    for name, data in raw_data.items():
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("Project names must be non-empty strings.")
        normalized[name] = _validate_project(name.strip(), data)

    return normalized
