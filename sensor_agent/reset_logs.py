#!/usr/bin/python3 -I
"""Restricted local reset broker. No network listener or caller-supplied paths."""
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys

LOG_ROOT = Path("/opt/zeek/logs")
SPOOL_ROOT = Path("/opt/zeek/spool/zeek")
STATE_ROOT = Path("/var/lib/nids-reset")
SOCKET_PATH = Path("/run/nids-reset/control.sock")


def command(*args, timeout=140, allowed=(0,)):
    result = subprocess.run(args, capture_output=True, timeout=timeout, check=False,
                            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
    if result.returncode not in allowed:
        raise RuntimeError("Zeek control command failed.")
    return result.returncode


def validate_root(root):
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise RuntimeError("Reset root is missing or redirected.")


def remove_logs(root):
    validate_root(root)
    removed = 0
    # Never recurse through symlinks or remove Zeek control/state/configuration.
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if not name.endswith((".log", ".log.gz")):
                continue
            if path.is_symlink():
                raise RuntimeError("Refusing a redirected log file.")
            path.resolve().relative_to(root)
            if not path.is_file():
                raise RuntimeError("Unexpected log entry.")
            path.unlink()
            removed += 1
    return removed


def receipt(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def reset(operation_id):
    if not re.fullmatch(r"[a-f0-9]{32}", operation_id):
        raise ValueError("Invalid reset identifier.")
    validate_root(LOG_ROOT)
    validate_root(SPOOL_ROOT)
    validate_root(STATE_ROOT)
    path = STATE_ROOT / f"{operation_id}.json"
    with (STATE_ROOT / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = json.loads(path.read_text()) if path.exists() else {"phase": "prepared", "removed": 0}
        if saved["phase"] == "completed":
            return {"status": "completed", "operation_id": operation_id}
        if saved["phase"] == "prepared":
            receipt(path, saved)
            command("/usr/bin/systemctl", "stop", "zeek.service")
            # An unmanaged Zeek process or lingering rotation hook makes deletion unsafe.
            if command("/usr/bin/pgrep", "-x", "zeek", allowed=(0, 1)) == 0:
                raise RuntimeError("Zeek is still running.")
            if command("/usr/bin/pgrep", "-f", "[ /]/opt/zeek/share/zeekctl/scripts/(post-terminate|archive-log)", allowed=(0, 1)) == 0:
                raise RuntimeError("Log rotation is still running.")
            removed = remove_logs(LOG_ROOT) + remove_logs(SPOOL_ROOT)
            saved = {"phase": "cleaned", "removed": removed}
            # Persist before starting capture: retries must never delete new traffic.
            receipt(path, saved)
        if saved["phase"] != "cleaned":
            raise RuntimeError("Invalid reset recovery state.")
        command("/usr/bin/systemctl", "start", "zeek.service", timeout=60)
        command("/usr/bin/systemctl", "is-active", "--quiet", "zeek.service", timeout=10)
        if command("/usr/bin/pgrep", "-x", "zeek", allowed=(0, 1)) != 0:
            raise RuntimeError("Capture did not restart.")
        receipt(path, {**saved, "phase": "completed"})
        return {"status": "completed", "operation_id": operation_id}


def serve(agent_uid):
    if os.geteuid() != 0 or agent_uid <= 0:
        raise RuntimeError("The reset broker needs root and a non-root agent UID.")
    validate_root(STATE_ROOT)
    SOCKET_PATH.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(SOCKET_PATH))
        os.chown(SOCKET_PATH, agent_uid, -1)
        os.chmod(SOCKET_PATH, 0o600)
        server.listen(4)
        while True:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(10)
                _, uid, _ = struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                try:
                    if uid != agent_uid:
                        raise PermissionError("Unauthorized local caller.")
                    data = b""
                    while not data.endswith(b"\n"):
                        chunk = connection.recv(512)
                        if not chunk or len(data) + len(chunk) > 1024:
                            raise ValueError("Invalid request.")
                        data += chunk
                    request = json.loads(data)
                    if set(request) != {"operation_id", "confirmation"} or request["confirmation"] != "RESET":
                        raise ValueError("Confirmation required.")
                    result = reset(request["operation_id"])
                except Exception:
                    # Do not return paths, subprocess output or environment details.
                    result = {"status": "failed"}
                try:
                    connection.sendall((json.dumps(result) + "\n").encode())
                except OSError:
                    pass  # The persisted receipt lets a disconnected caller retry.


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected the sensor service UID.")
    serve(int(sys.argv[1]))
