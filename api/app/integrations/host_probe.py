"""Bounded ICMP reachability check; never infer power state from a missing reply."""
import asyncio
import os
import subprocess
import sys
from typing import Literal
from urllib.parse import urlsplit

HostStatus = Literal["reachable", "unreachable", "unknown"]


def _probe(host: str) -> HostStatus:
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
               "stderr": subprocess.DEVNULL, "timeout": 3, "check": False}
    if sys.platform == "win32":
        # .NET returns an ICMP status without relying on localized ping output.
        script = "$p=New-Object System.Net.NetworkInformation.Ping; try { if ($p.Send($env:NIDS_SENSOR_PROBE_HOST,1000).Status -eq 'Success') { exit 0 } else { exit 1 } } catch { exit 2 } finally { $p.Dispose() }"
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
        options["env"] = {**os.environ, "NIDS_SENSOR_PROBE_HOST": host}
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        command = ["ping", "-n", "-c", "1", "-W", "1000" if sys.platform == "darwin" else "1", "--", host]
    try:
        result = subprocess.run(command, **options)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return "reachable" if result.returncode == 0 else "unreachable" if result.returncode == 1 else "unknown"


async def probe_host(base_url: str) -> HostStatus:
    host = urlsplit(base_url).hostname
    if not host:
        raise ValueError("Sensor URL must contain a hostname for the reachability probe.")
    # Works with Windows Uvicorn reload loops, which cannot launch async subprocesses.
    return await asyncio.to_thread(_probe, host)
