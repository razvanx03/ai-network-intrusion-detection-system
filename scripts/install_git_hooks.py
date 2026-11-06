"""Install the repository's local secret-scan hook without staging or committing."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
from urllib.request import urlopen
import zipfile


VERSION = "8.30.1"
# Official release checksums, pinned here rather than trusted from a moving URL.
RELEASES = {
    ("Windows", "x86_64"): (
        "windows_x64.zip",
        "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
        "gitleaks.exe",
    ),
    ("Linux", "x86_64"): (
        "linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
        "gitleaks",
    ),
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], encoding="utf-8"
    ).strip()


def main() -> None:
    repo = Path(__file__).resolve().parent.parent
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo:
        raise RuntimeError("Run this installer from its own AI NIDS checkout.")
    hook = repo / ".githooks" / "pre-commit"
    if not hook.is_file():
        raise RuntimeError("Missing .githooks/pre-commit; restore the source first.")

    configured = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
        capture_output=True, text=True, check=False,
    )
    if configured.returncode not in (0, 1):
        raise RuntimeError("Could not inspect the existing Git hooks configuration.")
    if configured.returncode == 0:
        current = Path(configured.stdout.strip()).expanduser()
        current = current if current.is_absolute() else repo / current
        if current.resolve() != hook.parent.resolve():
            raise RuntimeError("Another hooksPath is configured; integrate existing hooks first.")
    else:
        default_hooks = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks"))
        active = [p.name for p in default_hooks.iterdir()
                  if p.is_file() and not p.name.endswith(".sample")] if default_hooks.exists() else []
        if active:
            raise RuntimeError("Existing hooks would be displaced: " + ", ".join(active))

    arch = platform.machine().lower()
    arch = "x86_64" if arch in ("amd64", "x86_64") else arch
    release = RELEASES.get((platform.system(), arch))
    if release is None:
        raise RuntimeError("This installer supports Windows/Linux x86_64 only.")
    archive_name, expected, executable = release
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{archive_name}"
    print(f"Downloading Gitleaks {VERSION}; verifying pinned SHA256...")
    with urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError("Release checksum mismatch; hooks configuration was not changed.")
    if archive_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            binary = bundle.read(executable)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            member = bundle.extractfile(executable)
            if member is None:
                raise RuntimeError("Release executable is missing.")
            binary = member.read()

    tools = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "nids-tools"))
    tools.mkdir(parents=True, exist_ok=True)
    destination = tools / executable
    temporary = tools / (executable + ".installing")
    try:
        temporary.write_bytes(binary)
        temporary.chmod(0o755)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    version = subprocess.check_output([str(destination), "version"], text=True).strip()
    if version != VERSION:
        raise RuntimeError(f"Unexpected Gitleaks version: {version}")
    hook.chmod(hook.stat().st_mode | 0o111)
    git(repo, "config", "--local", "core.hooksPath", ".githooks")
    print("Enabled .githooks/pre-commit for this checkout only.")
    print("Staged changes will be scanned before each commit; scanner errors block the commit.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(f"Hook installation failed: {exc}", file=sys.stderr)
        sys.exit(1)
