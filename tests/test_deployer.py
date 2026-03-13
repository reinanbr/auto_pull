"""tests/test_deployer.py - Unit tests for deployment execution logic."""

from unittest.mock import MagicMock, patch

from autopull.deployer import deploy_project


def _sample_project() -> dict[str, str]:
    """Return a sample project configuration."""
    return {
        "path": "/var/www/my-app",
        "branch": "main",
        "compose_file": "docker-compose.yml",
        "secret": "irrelevant",
    }


@patch("autopull.deployer.open", create=True)
@patch("autopull.deployer.subprocess.Popen")
def test_deploy_success(mock_popen, mock_open, tmp_path, monkeypatch) -> None:
    """Return success when deploy script exits with code 0."""
    process = MagicMock()
    process.communicate.return_value = ("ok", None)
    process.returncode = 0
    mock_popen.return_value = process

    monkeypatch.setenv("AUTOPULL_LOG_DIR", str(tmp_path))
    success, code = deploy_project("my-app", _sample_project())

    assert success is True
    assert code == 0
    assert mock_popen.called
    assert mock_open.called


@patch("autopull.deployer.open", create=True)
@patch("autopull.deployer.subprocess.Popen")
def test_deploy_failure(mock_popen, mock_open, tmp_path, monkeypatch) -> None:
    """Return failure when deploy script exits with non-zero code."""
    process = MagicMock()
    process.communicate.return_value = ("failed", None)
    process.returncode = 1
    mock_popen.return_value = process

    monkeypatch.setenv("AUTOPULL_LOG_DIR", str(tmp_path))
    success, code = deploy_project("my-app", _sample_project())

    assert success is False
    assert code == 1
    assert mock_open.called
