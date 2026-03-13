"""Unit tests for HTTP webhook server behavior."""

import hashlib
import hmac
import json
from io import BytesIO
from unittest.mock import patch

from autopull.config import ConfigError
from autopull.server import AutoPullHandler, _load_projects_or_500


class _DummyHandler:
    """Small handler double to run do_POST without opening a socket."""

    def __init__(
        self,
        *,
        path: str,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        client_ip: str = "127.0.0.1",
    ) -> None:
        self.path = path
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.headers = headers or {}
        self.client_address = (client_ip, 12345)

        self.status_code: int | None = None
        self.sent_headers: dict[str, str] = {}

    def send_response(self, status_code: int) -> None:
        self.status_code = status_code

    def send_header(self, key: str, value: str) -> None:
        self.sent_headers[key] = value

    def end_headers(self) -> None:
        return


def _json_body(handler: _DummyHandler) -> dict[str, str]:
    """Decode the JSON body written by _write_json_response."""
    raw = handler.wfile.getvalue().decode("utf-8")
    return json.loads(raw)


def _github_signature(secret: str, payload: bytes) -> str:
    """Build a GitHub-compatible sha256 signature header value."""
    digest = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def test_load_projects_or_500_config_error() -> None:
    """Return None and write 500 JSON response on config error."""
    handler = _DummyHandler(path="/site")

    with patch(
        "autopull.server.load_config", side_effect=ConfigError("bad cfg")
    ):
        result = _load_projects_or_500(handler)

    assert result is None
    assert handler.status_code == 500
    assert _json_body(handler)["error"] == "Server configuration error"


def test_do_post_unknown_route_returns_404() -> None:
    """Reject invalid path structure before any config lookup."""
    handler = _DummyHandler(path="/site/extra")

    AutoPullHandler.do_POST(handler)

    assert handler.status_code == 404
    assert _json_body(handler) == {"error": "Unknown route"}


def test_do_post_missing_content_length_returns_400() -> None:
    """Require Content-Length for payload reads."""
    handler = _DummyHandler(path="/site")
    projects = {
        "site": {
            "path": "/var/www/site",
            "secret": "secret",
            "branch": "main",
            "compose_file": "docker-compose.yml",
        }
    }

    with patch("autopull.server._load_projects_or_500", return_value=projects):
        AutoPullHandler.do_POST(handler)

    assert handler.status_code == 400
    assert _json_body(handler) == {"error": "Missing Content-Length header"}


def test_do_post_invalid_signature_returns_401() -> None:
    """Reject webhook when HMAC signature validation fails."""
    payload = b'{"ref":"refs/heads/main"}'
    handler = _DummyHandler(
        path="/site",
        body=payload,
        headers={
            "Content-Length": str(len(payload)),
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    projects = {
        "site": {
            "path": "/var/www/site",
            "secret": "secret",
            "branch": "main",
            "compose_file": "docker-compose.yml",
        }
    }

    with patch("autopull.server._load_projects_or_500", return_value=projects):
        AutoPullHandler.do_POST(handler)

    assert handler.status_code == 401
    assert _json_body(handler) == {"error": "Invalid signature"}


def test_do_post_valid_signature_returns_202_and_starts_deploy() -> None:
    """Accept valid webhook and trigger background deployment."""
    secret = "secret"
    payload = b'{"ref":"refs/heads/main"}'
    signature = _github_signature(secret, payload)

    handler = _DummyHandler(
        path="/site",
        body=payload,
        headers={
            "Content-Length": str(len(payload)),
            "X-Hub-Signature-256": signature,
        },
    )
    projects = {
        "site": {
            "path": "/var/www/site",
            "secret": secret,
            "branch": "main",
            "compose_file": "docker-compose.yml",
        }
    }

    with patch("autopull.server._load_projects_or_500", return_value=projects):
        with patch("autopull.server.start_background_deploy") as mock_deploy:
            AutoPullHandler.do_POST(handler)

    assert handler.status_code == 202
    assert _json_body(handler) == {"status": "accepted"}
    mock_deploy.assert_called_once_with("site", projects["site"])
