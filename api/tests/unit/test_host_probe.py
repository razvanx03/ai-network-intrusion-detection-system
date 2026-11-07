import asyncio
import subprocess
from types import SimpleNamespace
import pytest
from app.integrations import host_probe as module


@pytest.mark.parametrize("code,status", [(0, "reachable"), (1, "unreachable"), (2, "unknown"), (127, "unknown")])
def test_posix_probe_is_bounded_and_uses_only_url_hostname(monkeypatch, code, status):
    monkeypatch.setattr(module.sys, "platform", "linux")
    calls = []
    def run(command, **options):
        calls.append((command, options))
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(module.subprocess, "run", run)
    assert asyncio.run(module.probe_host("https://192.0.2.1:8000/path")) == status
    command, options = calls[0]
    assert command == ["ping", "-n", "-c", "1", "-W", "1", "--", "192.0.2.1"]
    assert options["timeout"] == 3 and not options.get("shell")


def test_windows_probe_uses_dotnet_status_instead_of_localized_ping_text(monkeypatch):
    monkeypatch.setattr(module.sys, "platform", "win32")
    def run(command, **options):
        assert command[:4] == ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]
        assert "System.Net.NetworkInformation.Ping" in command[4]
        assert "Success" in command[4] and "192.0.2.1" not in command[4]
        assert options["env"]["NIDS_SENSOR_PROBE_HOST"] == "192.0.2.1"
        assert options["timeout"] == 3 and not options.get("shell")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, "run", run)
    assert asyncio.run(module.probe_host("http://192.0.2.1:8000")) == "reachable"


@pytest.mark.parametrize("error", [FileNotFoundError(), PermissionError(), subprocess.TimeoutExpired("ping", 3)])
def test_probe_failure_never_claims_ubuntu_is_offline(monkeypatch, error):
    def run(*args, **kwargs):
        raise error
    monkeypatch.setattr(module.subprocess, "run", run)
    assert asyncio.run(module.probe_host("http://192.0.2.1:8000")) == "unknown"


def test_missing_hostname_is_a_configuration_error():
    with pytest.raises(ValueError, match="hostname"):
        asyncio.run(module.probe_host("/relative"))
