#!/usr/bin/env python3
"""autopull/deployer.py - Deployment orchestration for AutoPull projects."""

import os
import subprocess
import threading
from datetime import datetime, timezone
from typing import Dict, Tuple

from autopull.logger import get_logger, project_logger_adapter

DEFAULT_LOG_DIR = "/var/log/autopull"


def _resolve_script_path() -> str:
    """Resolve deploy script path from env, system install, or local repository."""
    env_script = os.environ.get("AUTOPULL_DEPLOY_SCRIPT")
    if env_script:
        return env_script

    system_path = "/usr/lib/autopull/scripts/pull-and-deploy.sh"
    if os.path.exists(system_path):
        return system_path

    local_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "pull-and-deploy.sh")
    )
    return local_path


def _ensure_log_dir() -> str:
    """Ensure project log directory exists and return it."""
    target = os.environ.get("AUTOPULL_LOG_DIR", DEFAULT_LOG_DIR)
    try:
        os.makedirs(target, exist_ok=True)
        return target
    except OSError:
        fallback = "/tmp/autopull"
        os.makedirs(fallback, exist_ok=True)
        return fallback


def _project_log_path(project_name: str) -> str:
    """Build project-specific deployment log path."""
    safe_name = project_name.replace("/", "_")
    return os.path.join(_ensure_log_dir(), f"{safe_name}.log")


def deploy_project(project_name: str, project_config: Dict[str, str]) -> Tuple[bool, int]:
    """Run pull-and-deploy script and capture output in project log file."""
    logger = project_logger_adapter(get_logger(), project_name)
    script_path = _resolve_script_path()

    command = [
        script_path,
        project_config["path"],
        project_config["branch"],
        project_config["compose_file"],
    ]

    logger.info("Starting deployment command: %s", " ".join(command))

    timestamp = datetime.now(timezone.utc).isoformat()
    log_path = _project_log_path(project_name)

    try:
        process = subprocess.Popen(  # noqa: S603
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output, _ = process.communicate()
        exit_code = process.returncode
    except FileNotFoundError:
        output = f"[{timestamp}] Deploy script not found: {script_path}\n"
        exit_code = 127
    except Exception as exc:  # pylint: disable=broad-except
        output = f"[{timestamp}] Deployment failed before execution: {exc}\n"
        exit_code = 1

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(f"\n[{timestamp}] Running deployment for {project_name}\n")
        handle.write(output or "")
        handle.write(f"[{timestamp}] Exit code: {exit_code}\n")

    if exit_code == 0:
        logger.info("Deployment finished successfully.")
        return True, exit_code

    logger.error("Deployment failed with exit code %s.", exit_code)
    return False, exit_code


def start_background_deploy(project_name: str, project_config: Dict[str, str]) -> None:
    """Start deployment in a daemon thread so HTTP responses return immediately."""

    def _runner() -> None:
        deploy_project(project_name, project_config)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
