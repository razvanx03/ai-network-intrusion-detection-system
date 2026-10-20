#!/usr/bin/env bash
# Run INSIDE the Ubuntu VM after copying the agent, .env and Python .venv.
# Example for the existing VM (the deployed collector was renamed sensor_agent.py):
# sudo bash setup_sensor_autostart.sh --agent-dir /home/ubuntu/Desktop/nids_agent \
#   --script sensor_agent.py --user ubuntu --host 192.168.56.101
set -Eeuo pipefail
umask 077
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

readonly SERVICE=nids-sensor.service
readonly UNIT_PATH=/etc/systemd/system/nids-sensor.service
agent_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
agent_script=collector.py
agent_user="${SUDO_USER:-}"
agent_host=''
work_dir=''
backup_path=''

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
    cat <<'EOF'
Usage: sudo bash setup_sensor_autostart.sh --host MANAGEMENT_IP [options]
  --agent-dir DIR   Directory with the agent, .env and .venv (default: beside this helper)
  --script FILE     Python filename in that directory (default: collector.py)
  --user USER       Unprivileged service user (default: user invoking sudo)
  --host IP         Required local management IP; overrides AGENT_HOST for the service
  --help            Show this help without configuring anything

Prepare Zeek, the Python virtual environment and .env first. This helper installs
no packages, changes no network settings and never starts/stops Zeek or reboots.
EOF
}
cleanup() {
    if [[ -n "$work_dir" && -d "$work_dir" ]]; then
        rm -f -- "$work_dir/$SERVICE"
        rmdir -- "$work_dir"
    fi
}
trap cleanup EXIT
trap 'printf "ERROR: Setup failed at line %s. Inspect: sudo journalctl -u nids-sensor.service -n 60 --no-pager\n" "$LINENO" >&2' ERR

while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --agent-dir|--script|--user|--host)
            (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || die "Missing value for $1."
            case "$1" in
                --agent-dir) agent_dir="$2" ;;
                --script) agent_script="$2" ;;
                --user) agent_user="$2" ;;
                --host) agent_host="$2" ;;
            esac
            shift 2 ;;
        *) die "Unknown argument: $1. Use --help." ;;
    esac
done

[[ $EUID -eq 0 ]] || die 'Run inside Ubuntu using sudo bash setup_sensor_autostart.sh --host MANAGEMENT_IP.'
[[ -r /etc/os-release ]] || die 'Missing /etc/os-release.'
# shellcheck source=/dev/null
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] || die 'Ubuntu 24.04 is required.'
[[ -d /run/systemd/system ]] || die 'The VM must be booted with systemd.'
for tool in systemctl systemd-analyze runuser getent id flock readlink mktemp cmp cp install; do
    command -v "$tool" >/dev/null || die "Required command is missing: $tool"
done
[[ -n "$agent_host" ]] || die 'Supply --host with the Ubuntu management IP, for example 192.168.56.101.'
[[ "$agent_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || die 'Supply a valid unprivileged account using --user.'
id "$agent_user" >/dev/null 2>&1 || die "User does not exist: $agent_user"
[[ "$(id -u "$agent_user")" != 0 ]] || die 'The agent must not run as root.'
getent group zeek >/dev/null || die 'The zeek log-reading group must exist first.'
[[ -d "$agent_dir" ]] || die "Agent directory not found: $agent_dir"
agent_dir="$(readlink -f -- "$agent_dir")"
# Restrict paths so shell/systemd quoting and specifiers cannot change their meaning.
[[ "$agent_dir" =~ ^/[A-Za-z0-9_./-]+$ ]] || die 'Use an absolute agent path without spaces or special characters.'
[[ "$agent_script" =~ ^[A-Za-z0-9_-]+\.py$ ]] || die '--script must be a Python basename, for example collector.py.'
readonly PYTHON="$agent_dir/.venv/bin/python"
[[ -x "$PYTHON" ]] || die "Missing Python virtual environment: $PYTHON"
[[ -f "$agent_dir/$agent_script" && -f "$agent_dir/.env" ]] || die 'The agent script and its .env must exist in --agent-dir.'
[[ ! -L "$UNIT_PATH" ]] || die "Refusing to replace a symlink: $UNIT_PATH"

exec 9>/run/lock/nids-sensor-autostart.lock
flock -n 9 || die 'Another sensor autostart setup is already running.'
[[ -z "$(systemctl show "$SERVICE" -p DropInPaths --value)" ]] || die 'Existing service drop-ins require manual review before replacement.'

# Import, but do not launch, the collector as the SAME user/group as the service.
# This validates dependencies, .env, log access and the management IP before changes.
primary_group="$(id -gn "$agent_user")"
agent_port="$(runuser -u "$agent_user" -g "$primary_group" -G zeek -- \
    env AGENT_HOST="$agent_host" "$PYTHON" - "$agent_dir/$agent_script" "$agent_host" <<'PY'
import ipaddress
import os
from pathlib import Path
import runpy
import socket
import stat
import sys


def fail_walk(error):
    raise error


try:
    script = Path(sys.argv[1])
    host = ipaddress.ip_address(sys.argv[2])
    if host.is_unspecified or host.is_multicast:
        raise ValueError("use a specific local management IP, not a wildcard or multicast address")
    env_file = script.with_name(".env")
    if stat.S_IMODE(env_file.stat().st_mode) & 0o077:
        raise ValueError("protect .env first with chmod 600 and ensure the service user can read it")
    env_file.read_bytes()
    os.chdir(script.parent)
    module = runpy.run_path(str(script), run_name="nids_sensor_setup_check")
    port = module["PORT"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("AGENT_PORT must be between 1 and 65535")
    with socket.socket(socket.AF_INET6 if host.version == 6 else socket.AF_INET) as probe:
        probe.bind((str(host), 0))
    for root in (module["LOG_DIR"], module["CURRENT_LOG_DIR"]):
        # Opening directories/files detects permission failures rather than hiding them.
        for directory, _, names in os.walk(root, onerror=fail_walk):
            for name in names:
                if name == "conn.log" or (name.startswith("conn.") and name.endswith((".log", ".log.gz"))):
                    with (Path(directory) / name).open("rb") as stream:
                        stream.read(1)
    print(port)
except Exception as error:
    # Never print configuration values, source lines or a traceback containing secrets.
    sys.exit(f"Agent preflight failed ({type(error).__name__}). Check the management IP, .env permissions/settings, dependencies and Zeek log access.")
PY
)"
[[ "$agent_port" =~ ^[0-9]+$ ]] || die 'Agent preflight returned an invalid port.'

work_dir="$(mktemp -d /tmp/nids-sensor-setup.XXXXXXXX)"
cat > "$work_dir/$SERVICE" <<EOF
[Unit]
Description=AI NIDS Zeek log reader
Wants=network-online.target
After=network-online.target zeek.service

[Service]
Type=simple
User=$agent_user
SupplementaryGroups=zeek
WorkingDirectory=$agent_dir
Environment=AGENT_HOST=$agent_host
ExecStart=$PYTHON $agent_dir/$agent_script
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
EOF
systemd-analyze verify "$work_dir/$SERVICE"

existing_unit="$(systemctl show "$SERVICE" -p FragmentPath --value)"
if [[ -f "$UNIT_PATH" ]] && cmp -s -- "$work_dir/$SERVICE" "$UNIT_PATH"; then
    printf 'Service configuration already matches; no replacement needed.\n'
else
    if [[ -n "$existing_unit" && -f "$existing_unit" ]]; then
        backup_path="${UNIT_PATH}.backup-$(date +%Y%m%d-%H%M%S-%N)"
        cp -p -- "$existing_unit" "$backup_path"
        printf 'Previous unit backed up to: %s\n' "$backup_path"
    elif [[ -f "$UNIT_PATH" ]]; then
        backup_path="${UNIT_PATH}.backup-$(date +%Y%m%d-%H%M%S-%N)"
        cp -p -- "$UNIT_PATH" "$backup_path"
        printf 'Previous unit backed up to: %s\n' "$backup_path"
    fi
    install -o root -g root -m 0644 -- "$work_dir/$SERVICE" "$UNIT_PATH"
fi
systemctl daemon-reload
systemctl enable "$SERVICE"
# Restart the ONE managed service so a changed script or .env also takes effect.
# An unrelated manually started agent is never killed; a port conflict fails visibly.
systemctl restart "$SERVICE"

# Authenticate without passing the API key in arguments or printing it.
runuser -u "$agent_user" -g "$primary_group" -G zeek -- \
    "$PYTHON" - "$agent_dir/.env" "$agent_host" "$agent_port" <<'PY'
from dotenv import dotenv_values
import json
import sys
import time
import urllib.request

config = dotenv_values(sys.argv[1])
host = f"[{sys.argv[2]}]" if ":" in sys.argv[2] else sys.argv[2]
request = urllib.request.Request(
    f"http://{host}:{sys.argv[3]}/health", headers={"X-API-Key": config["API_KEY"]}
)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(15):
    try:
        with opener.open(request, timeout=2) as response:
            body = json.load(response)
        if body.get("status") != "ok" or body.get("service") != "zeek-sensor-agent":
            raise ValueError("Unexpected health response")
        break
    except Exception:
        if attempt == 14:
            sys.exit("Authenticated health check failed. Inspect journalctl -u nids-sensor.service.")
        time.sleep(1)
PY
systemctl is-active --quiet "$SERVICE" || die 'The service exited; inspect its journal (possibly a port conflict).'
systemctl is-enabled --quiet "$SERVICE" || die 'The service is not enabled at boot.'
printf '\nSUCCESS: %s is running and enabled at boot. Authenticated health check passed.\n' "$SERVICE"
printf 'Unit: %s\nManagement endpoint: %s:%s\n' "$UNIT_PATH" "$agent_host" "$agent_port"
printf 'Verify after reboot:\n  sudo systemctl status %s --no-pager\n' "$SERVICE"
printf '  sudo journalctl -u %s -n 60 --no-pager\n' "$SERVICE"
printf 'Restart=on-failure restarts a failed process; it does not detect a hung process or prove Zeek capture.\n'
