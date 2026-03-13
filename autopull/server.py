#!/usr/bin/env python3
"""autopull/server.py - HTTP webhook server for AutoPull deployments."""

import hashlib
import hmac
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict

from autopull.config import ConfigError, load_config
from autopull.deployer import start_background_deploy
from autopull.logger import get_logger, project_logger_adapter

LOGGER = get_logger()


def verify_signature(secret: str, payload: bytes, signature_header: str) -> bool:
    """Validate GitHub HMAC-SHA256 signature header."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    provided_signature = signature_header.split("=", 1)[1].strip()
    if not provided_signature:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, provided_signature)


def _load_projects_or_500(handler: BaseHTTPRequestHandler) -> Dict[str, Dict[str, str]] | None:
    """Load projects and return None after sending HTTP 500 on failure."""
    try:
        return load_config()
    except ConfigError as exc:
        LOGGER.error("Configuration error: %s", exc, extra={"project": "-"})
        response = {"error": "Server configuration error", "detail": str(exc)}
        _write_json_response(handler, 500, response)
        return None


def _write_json_response(
    handler: BaseHTTPRequestHandler, status_code: int, payload: Dict[str, str]
) -> None:
    """Write JSON response to client."""
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


class AutoPullHandler(BaseHTTPRequestHandler):
    """Handle inbound GitHub webhooks for project deployments."""

    server_version = "AutoPull/1.0"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        """Redirect default HTTP logs into project logger."""
        LOGGER.info(
            "%s - %s",
            self.client_address[0],
            format % args,
            extra={"project": "-"},
        )

    def do_POST(self) -> None:  # noqa: N802
        """Validate webhook signature and trigger project deployment."""
        project_name = self.path.strip("/")
        client_ip = self.client_address[0]

        if not project_name or "/" in project_name:
            _write_json_response(self, 404, {"error": "Unknown route"})
            LOGGER.warning(
                "Rejected request from %s path=%s result=404",
                client_ip,
                self.path,
                extra={"project": "-"},
            )
            return

        projects = _load_projects_or_500(self)
        if projects is None:
            return

        project_config = projects.get(project_name)
        if project_config is None:
            _write_json_response(self, 404, {"error": "Unknown project"})
            LOGGER.warning(
                "Rejected request from %s project=%s result=404",
                client_ip,
                project_name,
                extra={"project": project_name},
            )
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            _write_json_response(self, 400, {"error": "Missing Content-Length header"})
            return

        try:
            payload_len = int(content_length)
        except ValueError:
            _write_json_response(self, 400, {"error": "Invalid Content-Length header"})
            return

        payload = self.rfile.read(payload_len)
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(project_config["secret"], payload, signature):
            _write_json_response(self, 401, {"error": "Invalid signature"})
            LOGGER.warning(
                "Rejected request from %s project=%s result=401 invalid-signature",
                client_ip,
                project_name,
                extra={"project": project_name},
            )
            return

        adapter = project_logger_adapter(LOGGER, project_name)
        adapter.info("Accepted webhook from %s result=202", client_ip)
        start_background_deploy(project_name, project_config)
        _write_json_response(self, 202, {"status": "accepted"})


def run_server() -> None:
    """Start the HTTP server with host/port from environment."""
    host = os.environ.get("AUTOPULL_HOST", "0.0.0.0")
    port_raw = os.environ.get("AUTOPULL_PORT", "9000")
    try:
        port = int(port_raw)
    except ValueError:
        raise SystemExit("AUTOPULL_PORT must be an integer.")

    logging.getLogger("http.server").setLevel(logging.WARNING)

    server = ThreadingHTTPServer((host, port), AutoPullHandler)
    LOGGER.info(
        "AutoPull server listening on %s:%s",
        host,
        port,
        extra={"project": "-"},
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutdown requested by keyboard interrupt.", extra={"project": "-"})
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
