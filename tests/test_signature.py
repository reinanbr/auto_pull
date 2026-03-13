"""tests/test_signature.py - Unit tests for webhook HMAC signature validation."""

import hashlib
import hmac

from autopull.server import verify_signature


def test_valid_signature() -> None:
    """Accept a valid GitHub-style signature header."""
    secret = "super-secret"
    payload = b'{"ref":"refs/heads/main"}'
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_signature(secret, payload, f"sha256={digest}")


def test_invalid_signature() -> None:
    """Reject signature mismatch."""
    secret = "super-secret"
    payload = b'{"ref":"refs/heads/main"}'

    assert not verify_signature(secret, payload, "sha256=deadbeef")


def test_missing_prefix() -> None:
    """Reject non-GitHub signature format."""
    secret = "super-secret"
    payload = b"payload"

    assert not verify_signature(secret, payload, "deadbeef")
