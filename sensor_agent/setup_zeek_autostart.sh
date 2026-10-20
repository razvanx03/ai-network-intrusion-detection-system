#!/usr/bin/env bash
# Run INSIDE the Ubuntu VM after installing and deploying Zeek:
#   sudo bash setup_zeek_autostart.sh
# This configures startup only; it never installs Zeek or changes its policies.
set -Eeuo pipefail
umask 077
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

readonly ZEEKCTL=/opt/zeek/bin/zeekctl
readonly NODE_CONFIG=/opt/zeek/etc/node.cfg
readonly ZEEKCTL_SCRIPTS=/opt/zeek/share/zeekctl/scripts
readonly UNIT_PATH=/etc/systemd/system/zeek.service
readonly SERVICE=zeek.service
work_dir=''
backup_path=''

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
cleanup() {
    if [[ -n "$work_dir" && -d "$work_dir" ]]; then
        # Only this invocation's private temporary directory is removed.
        rm -f -- "$work_dir/zeek.service"
        rmdir -- "$work_dir"
    fi
}
trap cleanup EXIT
trap 'printf "ERROR: Setup failed at line %s. Inspect: sudo journalctl -u zeek.service -n 60 --no-pager\n" "$LINENO" >&2' ERR

[[ $EUID -eq 0 ]] || die "Run inside Ubuntu with: sudo bash $0"
[[ -r /etc/os-release ]] || die 'Missing /etc/os-release.'
# shellcheck source=/dev/null
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] || die 'Ubuntu 24.04 is required.'
[[ -d /run/systemd/system ]] || die 'The VM must be booted with systemd.'
[[ -f /sys/fs/cgroup/cgroup.controllers ]] || die 'This helper requires the cgroup v2 hierarchy used by Ubuntu 24.04.'
for tool in systemctl python3 ip pgrep flock mktemp cmp install cp timeout; do
    command -v "$tool" >/dev/null || die "Required command is missing: $tool"
done
[[ -x "$ZEEKCTL" && -x /opt/zeek/bin/zeek ]] || die 'Zeek and ZeekControl must already be installed in /opt/zeek.'
[[ -r "$NODE_CONFIG" ]] || die "Missing or unreadable $NODE_CONFIG."
# These paths were checked against the installed ZeekControl 9.0 package.
# Refuse a different layout before installing a unit with an invalid stop hook.
for helper in helpers/start run-zeek post-terminate archive-log; do
    [[ -x "$ZEEKCTL_SCRIPTS/$helper" ]] || die "Expected ZeekControl helper is missing or not executable: $ZEEKCTL_SCRIPTS/$helper"
done

# Serialize two copies of this setup script. ZeekControl also has its own lock.
exec 9>/run/lock/nids-zeek-autostart.lock
flock -n 9 || die 'Another Zeek autostart setup is already running.'

# Parse the existing configuration without changing it or running deploy.
node_name="$(python3 - "$NODE_CONFIG" <<'PY'
import configparser
import re
import sys

config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=("#", ";"))
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        config.read_file(stream)
    sections = config.sections()
    if len(sections) != 1:
        raise ValueError("exactly one standalone node is required")
    name = sections[0]
    node = config[name]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("unsupported node name")
    if node.get("type", "").strip().lower() != "standalone":
        raise ValueError("node type must be standalone")
    if node.get("host", "").strip().lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("the standalone node must use a local host")
    if node.get("interface", "").strip() != "enp0s8":
        raise ValueError("expected capture interface enp0s8; review node.cfg manually")
    if node.get("lb_procs", "").strip():
        raise ValueError("load-balanced deployments are not supported by this helper")
    print(name)
except (OSError, ValueError, configparser.Error) as error:
    sys.exit(f"Invalid node.cfg: {error}. Configuration was not changed.")
PY
)"
ip link show dev enp0s8 >/dev/null || die 'Capture interface enp0s8 does not exist.'

# Do not silently override masks, aliases or service drop-ins.
[[ ! -L "$UNIT_PATH" ]] || die "$UNIT_PATH is a symlink or mask; review it manually."
drop_ins="$(systemctl show "$SERVICE" --property=DropInPaths --value)"
[[ -z "$drop_ins" ]] || die "Existing service overrides must be reviewed first: $drop_ins"
active_state="$(systemctl show "$SERVICE" --property=ActiveState --value)"
case "$active_state" in
    active|inactive|failed) ;;
    *) die "Service state is '$active_state'; wait for any pending start/stop job." ;;
esac

# Starting an already-running Zeek through zeekctl does not move its process
# into systemd's cgroup. Refuse that case rather than claiming ownership.
if [[ "$active_state" != active ]] && pgrep -x zeek >/dev/null; then
    die 'Zeek is already running outside zeek.service. Stop it manually with sudo /opt/zeek/bin/zeekctl stop, then rerun this script.'
fi

work_dir="$(mktemp -d /tmp/nids-zeek-autostart.XXXXXXXX)"
cat > "$work_dir/zeek.service" <<'UNIT'
[Unit]
Description=Zeek standalone network monitor managed by ZeekControl
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
WorkingDirectory=/opt/zeek
Environment=PATH=/opt/zeek/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStartPre=/usr/bin/test -d /sys/class/net/enp0s8
ExecStart=/opt/zeek/bin/zeekctl start
ExecStop=/opt/zeek/bin/zeekctl stop
# ZeekControl may archive logs asynchronously after stop returns. Wait before
# systemd cleans up remaining processes in this service's cgroup.
# Multiple ExecStop commands execute sequentially. This second command only
# waits for this /opt/zeek installation's helpers; it does not signal them.
ExecStop=/usr/bin/timeout 120 /bin/sh -c 'while /usr/bin/pgrep -f "[ /]/opt/zeek/share/zeekctl/scripts/(post-terminate|archive-log)" >/dev/null; do /usr/bin/sleep 1; done'
TimeoutStartSec=180
TimeoutStopSec=180
KillMode=control-group

[Install]
WantedBy=multi-user.target
UNIT

existing_fragment="$(systemctl show "$SERVICE" --property=FragmentPath --value)"
if [[ -f "$UNIT_PATH" ]] && cmp -s "$work_dir/zeek.service" "$UNIT_PATH"; then
    printf 'The service file is already up to date.\n'
else
    [[ "$active_state" != active ]] || die 'An active service has a different definition. Review and stop that service manually before replacing it.'
    # Back up the effective unit, including a vendor unit if there is no local file.
    source_path="$UNIT_PATH"
    if [[ ! -f "$source_path" ]]; then
        source_path="$existing_fragment"
    fi
    if [[ -n "$source_path" && -f "$source_path" ]]; then
        backup_path="${UNIT_PATH}.backup.$(date -u +%Y%m%dT%H%M%SZ).$$"
        [[ ! -e "$backup_path" ]] || die "Backup already exists: $backup_path"
        cp -p -- "$source_path" "$backup_path"
        cmp -s "$source_path" "$backup_path" || die 'Service backup verification failed.'
        printf 'Service backup: %s\n' "$backup_path"
    fi
    install -o root -g root -m 0644 "$work_dir/zeek.service" "$UNIT_PATH"
    printf 'Installed %s\n' "$UNIT_PATH"
fi

systemctl daemon-reload
systemctl enable "$SERVICE"

# RemainAfterExit can say active even after Zeek crashes. Rerunning this helper
# repairs that stale state; a healthy service is left running without restart.
if systemctl is-active --quiet "$SERVICE"; then
    if ! pgrep -x zeek >/dev/null; then
        printf 'Service is active but Zeek is absent; restarting via systemd.\n'
        systemctl restart "$SERVICE"
    else
        printf 'Service is already active; verifying the existing Zeek process.\n'
    fi
else
    systemctl start "$SERVICE"
fi

systemctl is-enabled --quiet "$SERVICE" || die 'Service is not enabled at boot.'
systemctl is-active --quiet "$SERVICE" || die 'Service is not active.'
systemctl --no-pager --full status "$SERVICE"
status_output="$("$ZEEKCTL" status)" || {
    printf '%s\n' "$status_output" >&2
    die 'ZeekControl did not report a healthy running node.'
}
printf '%s\n' "$status_output"

# Check the reported PID, executable, capture interface, and service cgroup.
# A generic pgrep alone could match an unrelated Zeek process.
service_cgroup="$(systemctl show "$SERVICE" --property=ControlGroup --value)"
python3 - "$node_name" "$service_cgroup" "$status_output" <<'PY'
import os
from pathlib import Path
import sys

name, group, output = sys.argv[1:]
rows = [line.split() for line in output.splitlines() if line.split()[:1] == [name]]
if len(rows) != 1 or len(rows[0]) < 5 or rows[0][1] != "standalone" or rows[0][3] != "running":
    sys.exit("ERROR: Expected exactly one running standalone node in ZeekControl status.")
pid = rows[0][4]
if not pid.isdecimal() or not group or group == "/":
    sys.exit("ERROR: Invalid PID or service cgroup.")
try:
    process = Path("/proc") / pid
    if os.path.realpath(process / "exe") != os.path.realpath("/opt/zeek/bin/zeek"):
        raise ValueError("the reported PID is not /opt/zeek/bin/zeek")
    memberships = [line.split(":", 2)[2] for line in (process / "cgroup").read_text().splitlines()
                   if line.startswith("0::")]
    # nohup/backgrounding preserves cgroup membership. A process launched by
    # systemd's ExecStart must remain in this unit's unified cgroup hierarchy.
    if len(memberships) != 1 or not (memberships[0] == group or memberships[0].startswith(group + "/")):
        raise ValueError(f"expected service cgroup {group}, found {memberships}; do not launch Zeek manually alongside systemd")
    arguments = (process / "cmdline").read_bytes().split(b"\0")
    if not any(arguments[i:i + 2] == [b"-i", b"enp0s8"] for i in range(len(arguments) - 1)):
        raise ValueError("Zeek is not capturing on enp0s8")
except (OSError, ValueError) as error:
    sys.exit(f"ERROR: Process verification failed: {error}")
print(f"Verified Zeek PID {pid}, interface enp0s8, owned by {group}.")
PY

cat <<'MESSAGE'

SUCCESS: Zeek is running and zeek.service is enabled for future boots.
No reboot was performed. Zeek policies and network settings were not changed.

IMPORTANT: Type=oneshot with RemainAfterExit=yes does not monitor Zeek after
startup. systemd can still report active (exited) if Zeek later crashes.
Use ZeekControl status and the process check below to verify actual operation.
No automatic crash-recovery timer or cron job was installed.

After your next manual reboot, run:
  sudo systemctl is-enabled zeek.service
  sudo systemctl status zeek.service --no-pager
  sudo /opt/zeek/bin/zeekctl status
  pgrep -a -x zeek
  sudo journalctl -b -u zeek.service --no-pager

For subsequent manual lifecycle operations, use:
  sudo systemctl start zeek.service
  sudo systemctl stop zeek.service
  sudo systemctl restart zeek.service
MESSAGE
