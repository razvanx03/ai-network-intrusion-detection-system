#!/usr/bin/env bash
: <<'NIDS_SETUP_OVERVIEW'
/*
Ubuntu VM setup: the four former setup scripts are merged into this ONE file.
  1. Gateway: persistent internal IPv4 address, forwarding, NAT and firewall rules.
  2. Zeek: install the 9.0 packages, configure standalone capture and JSON logs.
  3. Zeek autostart: prepare capture offloads before every systemd start.
  4. Sensor autostart: prepare Python, credentials and log access, then run collector.py.

Run INSIDE Ubuntu 24.04, preferably from its VM console:
  sudo bash setup_vm.sh --management-ip 192.168.56.101
Copy the sensor_agent directory, including reset_logs.py and nids-reset.service, first. An optional
.env beside them supplies the existing API key; otherwise a fresh key is generated.
The management address must already exist on the host-only adapter. VirtualBox
adapters and the Windows client's network settings are configured separately.
No automatic reboot, automatic traffic analysis or model installation is performed.
The quoted block makes this C-style comment notation valid inside a Bash script.
*/
NIDS_SETUP_OVERVIEW
set -Eeuo pipefail
umask 077
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SOURCE_DIR
readonly ZEEK_DIR=/opt/zeek
readonly AGENT_DIR=/opt/nids-sensor
readonly CAPTURE_HELPER=/usr/local/sbin/nids-zeek-capture
readonly RESET_HELPER=/usr/local/libexec/nids-reset-logs.py
readonly NETPLAN_FILE=/etc/netplan/99-nids-lab.yaml
readonly REPO_URL=https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04
external_if=enp0s3
internal_if=enp0s8
management_if=enp0s9
internal_cidr=192.168.50.1/24
management_ip=''
agent_user="${SUDO_USER:-}"
agent_port=8000
env_source=''
check_only=0
work_dir=''
backup_dir=''
stage=preflight
declare -A saved_files=()

die() { printf 'ERROR [%s]: %s\n' "$stage" "$*" >&2; exit 1; }
usage() {
    cat <<'HELP'
Usage: sudo bash setup_vm.sh --management-ip IP [options]
  --management-ip IP    Existing IPv4 address of the host-only management adapter
  --management-if IF    Management adapter (default: enp0s9)
  --external-if IF      NAT/internet adapter (default: enp0s3)
  --internal-if IF      Zeek/client-LAN adapter (default: enp0s8)
  --internal-cidr CIDR  Persistent gateway address (default: 192.168.50.1/24)
  --agent-user USER     Existing non-root account (default: user invoking sudo)
  --agent-port PORT     Sensor HTTP port (default: 8000)
  --env-file FILE       Existing sensor .env; preserve its API key and request limits
  --check               Read-only preflight, without installing/configuring anything
  --help                Show this help

Ubuntu 24.04 with systemd and three configured VM adapters is required. This
script manages the dedicated client LAN, not the external/management addresses.
Use a fresh VM or a simple existing standalone Zeek installation. Active UFW,
firewalld/nftables managers, custom overrides and complex netplan setups are refused.
HELP
}
while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --check) check_only=1; shift ;;
        --management-ip|--management-if|--external-if|--internal-if|--internal-cidr|--agent-user|--agent-port|--env-file)
            if (($# < 2)); then die "Missing value for $1."; fi
            [[ -n "$2" && "$2" != --* ]] || die "Missing value for $1."
            case "$1" in
                --management-ip) management_ip="$2" ;;
                --management-if) management_if="$2" ;;
                --external-if) external_if="$2" ;;
                --internal-if) internal_if="$2" ;;
                --internal-cidr) internal_cidr="$2" ;;
                --agent-user) agent_user="$2" ;;
                --agent-port) agent_port="$2" ;;
                --env-file) env_source="$2" ;;
            esac
            shift 2 ;;
        *) die "Unknown argument: $1. Use --help." ;;
    esac
done

[[ $EUID -eq 0 ]] || die 'Run inside the VM using sudo bash setup_vm.sh --management-ip IP.'
[[ -r /etc/os-release ]] || die 'Missing /etc/os-release.'
# shellcheck source=/dev/null
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] || die 'Ubuntu 24.04 is required.'
case "$(dpkg --print-architecture)" in amd64|arm64) ;; *) die 'The selected Zeek repository requires amd64 or arm64.' ;; esac
[[ -d /run/systemd/system && -f /sys/fs/cgroup/cgroup.controllers ]] || die 'systemd with cgroup v2 is required.'
for tool in ip python3 systemctl systemd-analyze systemd-escape netplan flock getent id runuser install cmp cp pgrep; do
    command -v "$tool" >/dev/null || die "Required command is missing: $tool"
done
[[ "$agent_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || die 'Supply an existing unprivileged --agent-user.'
id "$agent_user" >/dev/null 2>&1 || die "Unknown account: $agent_user"
[[ "$(id -u "$agent_user")" != 0 ]] || die 'The sensor must not run as root.'
[[ "$agent_port" =~ ^[0-9]+$ && ${#agent_port} -le 5 ]] || die 'Invalid --agent-port.'
((10#$agent_port >= 1024 && 10#$agent_port <= 65535)) || die 'Use an unprivileged port between 1024 and 65535.'
agent_port=$((10#$agent_port))
for iface in "$external_if" "$internal_if" "$management_if"; do
    [[ "$iface" =~ ^[a-zA-Z0-9_-]+$ && ${#iface} -le 15 ]] || die "Unsupported interface name: $iface"
    ip link show dev "$iface" >/dev/null || die "Interface is absent: $iface"
done
[[ "$external_if" != "$internal_if" && "$external_if" != "$management_if" && "$internal_if" != "$management_if" ]] || die 'The three interfaces must be distinct.'
[[ -f "$SOURCE_DIR/provision_tls.py" && -f "$SOURCE_DIR/collector.py" && -f "$SOURCE_DIR/requirements.txt" ]] || die 'Copy collector.py and requirements.txt beside this script.'
for path in "$AGENT_DIR" "$AGENT_DIR/.venv" "$AGENT_DIR/.env"; do
    [[ ! -L "$path" ]] || die "Refusing a symlink at $path"
done
for path in "$ZEEK_DIR" "$ZEEK_DIR/logs" "$ZEEK_DIR/spool"; do
    [[ ! -L "$path" ]] || die "Custom symlinked Zeek layout requires manual integration: $path"
done
if [[ -n "$env_source" ]]; then
    [[ -f "$env_source" && -r "$env_source" ]] || die '--env-file must identify a readable sensor configuration.'
    env_source="$(readlink -f -- "$env_source")"
elif [[ -f "$AGENT_DIR/.env" ]]; then
    env_source="$AGENT_DIR/.env"
elif [[ -f "$SOURCE_DIR/.env" ]]; then
    env_source="$SOURCE_DIR/.env"
fi
if [[ -n "$env_source" ]]; then
    # Validate the simple sensor dotenv format without requiring an installed
    # Python environment or modifying files/packages first. No secret is echoed.
    python3 - "$env_source" <<'PY'
from pathlib import Path
import re
import shlex
import sys
try:
    values = {}
    for line in Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'\s*(?:export\s+)?([A-Z_]+)\s*=(.*)', line)
        if not match or match[1] in values:
            raise ValueError('use unique KEY=value lines; multiline settings are unsupported')
        tokens = shlex.split(match[2], comments=True)
        if len(tokens) != 1:
            raise ValueError('every setting must contain one nonempty value')
        values[match[1]] = tokens[0]
    required = ('API_KEY', 'AGENT_HOST', 'AGENT_PORT', 'ZEEK_LOG_DIR', 'MAX_BATCH_RECORDS', 'MAX_BATCH_BYTES', 'MAX_LINE_BYTES')
    if any(not values.get(key) for key in required):
        raise ValueError('all settings from the sensor .env.example are required')
    if not re.fullmatch(r'[A-Za-z0-9._~-]{32,256}', values['API_KEY']) or values['API_KEY'].startswith('REPLACE_'):
        raise ValueError('replace the API key placeholder with a real URL-safe secret')
    if values['ZEEK_LOG_DIR'] != '/opt/zeek/logs':
        raise ValueError('only the /opt/zeek/logs layout is supported')
    limits = [values[key] for key in ('MAX_BATCH_RECORDS', 'MAX_BATCH_BYTES', 'MAX_LINE_BYTES')]
    if any(not re.fullmatch(r'[0-9]+', value) for value in limits):
        raise ValueError('request budgets must be positive integers')
    records, size, line = map(int, limits)
    if not (500 <= records <= 1000 and 1024 <= size <= 16*1024*1024 and 1024 <= line <= size):
        raise ValueError('request budgets are invalid or incompatible with backend batches of 500')
except (OSError, ValueError):
    sys.exit('Sensor .env preflight failed. Use unique nonempty settings from .env.example, a real API key, standard log path and valid request limits. No secret was printed or replaced.')
PY
fi
for path in "$NETPLAN_FILE" "$CAPTURE_HELPER" "$RESET_HELPER" /etc/systemd/system/nids-reset.service /etc/systemd/system/zeek.service /etc/systemd/system/nids-sensor.service /etc/sysctl.d/99-nids-gateway.conf; do
    [[ ! -L "$path" ]] || die "Refusing a symlink/mask at $path"
done
for unit in zeek.service nids-sensor.service nids-reset.service; do
    [[ -z "$(systemctl show "$unit" -p DropInPaths --value)" ]] || die "Review existing overrides for $unit first."
    case "$(systemctl show "$unit" -p ActiveState --value)" in
        active|inactive|failed) ;;
        *) die "Wait for the pending start/stop of $unit." ;;
    esac
done
if systemctl is-active --quiet firewalld.service || systemctl is-active --quiet nftables.service || { command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; }; then
    die 'An active firewall manager requires explicit policy integration; it will not be disabled or bypassed.'
fi
if pgrep -x zeek >/dev/null && ! systemctl is-active --quiet zeek.service; then
    die 'Zeek runs outside zeek.service. Stop it with zeekctl stop before setup.'
fi
if [[ -e "$ZEEK_DIR" ]]; then
    [[ -x "$ZEEK_DIR/bin/zeek" && -x "$ZEEK_DIR/bin/zeekctl" ]] || die 'Incomplete /opt/zeek installation; inspect it first.'
    [[ "$("$ZEEK_DIR/bin/zeek" --version 2>&1)" == *'version 9.0.'* ]] || die 'This setup supports the Zeek 9.0 package series only.'
fi

# Validate address roles before changing network configuration. CLI values cannot
# inject shell, netplan or systemd syntax. No management wildcard is accepted.
network_preflight() {
python3 - "$management_ip" "$internal_cidr" "$external_if" "$internal_if" "$management_if" "$agent_port" <<'PY'
import ipaddress
import json
import subprocess
import socket
import sys
import yaml

try:
    management = ipaddress.IPv4Address(sys.argv[1])
    internal = ipaddress.IPv4Interface(sys.argv[2])
    private = tuple(ipaddress.IPv4Network(value) for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    if not any(management in network for network in private):
        raise ValueError('management IP must be a specific private IPv4 address')
    if not any(internal.network.subnet_of(network) for network in private) or internal.network.prefixlen not in range(16, 31) or internal.ip in (internal.network.network_address, internal.network.broadcast_address):
        raise ValueError('client gateway must be a usable private address with prefix /16 through /30')
    addresses = json.loads(subprocess.check_output(['ip', '-j', '-4', 'address', 'show'], text=True))
    interfaces = {row['ifname']: [ipaddress.IPv4Interface(f"{a['local']}/{a['prefixlen']}")
        for a in row['addr_info'] if a['family'] == 'inet'] for row in addresses}
    matches = [value for value in interfaces.get(sys.argv[5], []) if value.ip == management]
    if len(matches) != 1:
        raise ValueError('management IP must already exist on the specified management adapter')
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'nids-sensor.service']).returncode:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((str(management), int(sys.argv[6])))
    for name in (sys.argv[3], sys.argv[5]):
        if any(internal.network.overlaps(value.network) for value in interfaces.get(name, [])):
            raise ValueError('client subnet overlaps the external or management subnet')
    defaults = json.loads(subprocess.check_output(['ip', '-j', '-4', 'route', 'show', 'default'], text=True))
    if not defaults or any(route.get('dev') != sys.argv[3] for route in defaults):
        raise ValueError('the IPv4 default route must use only the external/NAT adapter')
    document = yaml.safe_load(subprocess.check_output(['netplan', 'get'], text=True))
    if not isinstance(document, dict) or not isinstance(document.get('network'), dict):
        raise ValueError('netplan must report a valid network configuration')
    network = document['network']
    ethernets = network.get('ethernets', {})
    if not isinstance(ethernets, dict):
        raise ValueError('netplan ethernet configuration must be a mapping')
    matches_internal = [settings for name, settings in ethernets.items()
        if name == sys.argv[4] or settings.get('match', {}).get('name') == sys.argv[4]]
    if len(matches_internal) > 1:
        raise ValueError('multiple netplan entries match the internal adapter')
    settings = matches_internal[0] if matches_internal else {}
    renderer = settings.get('renderer', network.get('renderer', 'networkd'))
    method = 'network-manager' if renderer == 'NetworkManager' else 'netplan'
    if method == 'network-manager':
        if subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager.service']).returncode:
            raise ValueError('netplan selects NetworkManager but its service is not active')
        subprocess.check_output(['nmcli', '-g', 'GENERAL.STATE', 'device', 'show', sys.argv[4]], text=True)
    elif settings.get('match') or settings.get('set-name'):
        raise ValueError('matched/renamed networkd adapters require manual integration')
    if settings.get('routes') or settings.get('gateway4') or settings.get('gateway6'):
        raise ValueError('internal adapter has custom routes; inspect them before setup')
    if any(ipaddress.ip_interface(value) != internal for value in settings.get('addresses', [])):
        raise ValueError('internal adapter has a different static address; inspect it before setup')
    if any(network.get(kind) for kind in ('bridges', 'bonds', 'vlans')):
        raise ValueError('bridge/bond/VLAN netplan configurations require manual integration')
    print(internal.network, matches[0].network, method)
except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
    sys.exit(f'Network preflight failed: {error}')
PY
}
network_info="$(network_preflight)"
read -r client_subnet management_subnet network_method <<< "$network_info"
if [[ -f "$ZEEK_DIR/etc/node.cfg" ]]; then
    python3 - "$ZEEK_DIR/etc/node.cfg" <<'PY'
import configparser
import sys
config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=('#', ';'))
config.read(sys.argv[1])
if config.sections() != ['zeek'] or config['zeek'].get('type', '').strip() != 'standalone' or config['zeek'].get('host', '').strip() not in ('localhost', '127.0.0.1', '::1') or config['zeek'].get('lb_procs', '').strip():
    sys.exit('Only a single local [zeek] standalone node is supported; existing configuration was not changed.')
PY
fi
printf 'Plan: %s -> %s (%s); management %s on %s; sensor user %s, port %s.\n' "$internal_if" "$external_if" "$internal_cidr" "$management_ip" "$management_if" "$agent_user" "$agent_port"
printf 'Internal interface configuration: %s (existing renderer retained).\n' "$network_method"
if ((check_only)); then
    printf 'Read-only preflight passed. No configuration, packages or services were changed.\n'
    exit 0
fi

exec 9>/run/lock/nids-vm-setup.lock
flock -n 9 || die 'Another VM setup is already running.'
work_dir="$(mktemp -d /tmp/nids-vm-setup.XXXXXXXX)"
backup_dir="$(mktemp -d /var/backups/nids-vm-setup.XXXXXXXX)"
cleanup() {
    if [[ "$work_dir" == /tmp/nids-vm-setup.* && -d "$work_dir" ]]; then rm -rf -- "$work_dir"; fi
}
trap cleanup EXIT
trap 'printf "ERROR [%s] at line %s. Completed stages are retained; inspect %s and rerun after correcting the failure.\n" "$stage" "$LINENO" "$backup_dir" >&2' ERR
backup_file() {
    local path="$1"
    [[ -z "${saved_files[$path]+yes}" ]] || return 0
    [[ ! -L "$path" ]] || die "Refusing to overwrite symlink: $path"
    if [[ -e "$path" ]]; then
        [[ -f "$path" ]] || die "Expected a regular file: $path"
        cp -p --parents -- "$path" "$backup_dir"
    else
        printf '%s\n' "$path" >> "$backup_dir/previously-absent.txt"
    fi
    saved_files["$path"]=1
}
write_file() {
    local source="$1" target="$2" mode="$3"
    [[ ! -L "$target" ]] || die "Refusing to overwrite symlink: $target"
    if [[ ! -f "$target" ]] || ! cmp -s -- "$source" "$target"; then
        backup_file "$target"
        install -o root -g root -m "$mode" -- "$source" "$target"
    else
        chmod "$mode" "$target"
        chown root:root "$target"
    fi
}

stage=packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
# Suppress package prompts and avoid saving firewall state before our own rules.
printf 'iptables-persistent iptables-persistent/autosave_v4 boolean false\niptables-persistent iptables-persistent/autosave_v6 boolean false\n' | debconf-set-selections
# Fresh boots can still be applying unattended security updates. Let apt wait
# for dpkg's lock for a bounded interval; never remove locks or stop the updater.
apt-get -o DPkg::Lock::Timeout=300 install -y curl gpg ca-certificates ethtool iptables iptables-persistent python3-venv python3-yaml acl
# Stop only the existing managed instances before changing capture/network state.
for unit in nids-sensor.service nids-reset.service zeek.service; do
    if [[ "$(systemctl show "$unit" -p LoadState --value)" != not-found ]]; then systemctl stop "$unit"; fi
done
pgrep -x zeek >/dev/null && die 'An unmanaged Zeek process remains; stop it manually before setup.'

# -------------------- 1/4: GATEWAY --------------------
stage=gateway
netplan get > "$backup_dir/netplan-before.yaml"
if [[ "$network_method" == network-manager ]]; then
    # Ubuntu Desktop/NetworkManager writes its own netplan-backed profiles.
    # Use its API rather than changing renderers or replacing desktop networking.
    cp -a /etc/netplan "$backup_dir/netplan-files-before"
    connection_uuid="$(nmcli -g GENERAL.CON-UUID device show "$internal_if")"
    if [[ -z "$connection_uuid" || "$connection_uuid" == -- ]]; then
        profile="nids-lab-$internal_if"
        if connection_uuid="$(nmcli -g connection.uuid connection show "$profile" 2>/dev/null)"; then
            [[ "$(nmcli -g connection.interface-name connection show uuid "$connection_uuid")" == "$internal_if" ]] || die 'Existing NIDS profile belongs to a different adapter.'
        else
            nmcli connection add type ethernet ifname "$internal_if" con-name "$profile" connection.autoconnect-priority 100 ipv4.method manual ipv4.addresses "$internal_cidr" ipv4.never-default yes
            connection_uuid="$(nmcli -g connection.uuid connection show "$profile")"
        fi
    fi
    [[ "$connection_uuid" =~ ^[a-fA-F0-9-]{36}$ ]] || die 'NetworkManager did not return a connection UUID.'
    nmcli connection show uuid "$connection_uuid" > "$backup_dir/internal-connection-before.txt"
    nmcli connection modify uuid "$connection_uuid" ipv4.method manual ipv4.addresses "$internal_cidr" ipv4.gateway '' ipv4.never-default yes ipv4.dns '' ipv4.ignore-auto-dns yes connection.autoconnect yes connection.autoconnect-priority 100
    nmcli connection up uuid "$connection_uuid" ifname "$internal_if"
else
cat > "$work_dir/netplan.yaml" <<EOF
network:
  version: 2
  ethernets:
    $internal_if:
      dhcp4: false
      dhcp6: false
      addresses: [$internal_cidr]
      optional: true
EOF
    # Reuse an already-correct static definition instead of merging a duplicate
    # address into another netplan file's address sequence.
    if ! python3 - "$internal_if" "$internal_cidr" <<'PY'
import subprocess
import sys
import yaml
document = yaml.safe_load(subprocess.check_output(['netplan', 'get'], text=True))
settings = document['network'].get('ethernets', {}).get(sys.argv[1], {})
sys.exit(0 if settings.get('addresses') == [sys.argv[2]] and not settings.get('dhcp4', False) else 1)
PY
    then
        write_file "$work_dir/netplan.yaml" "$NETPLAN_FILE" 0600
        if ! netplan generate; then
            if [[ -f "$backup_dir$NETPLAN_FILE" ]]; then cp -p -- "$backup_dir$NETPLAN_FILE" "$NETPLAN_FILE"; else rm -f -- "$NETPLAN_FILE"; fi
            die 'Netplan validation failed; the managed file was restored. No netplan apply was issued.'
        fi
        netplan apply
    fi
fi
network_preflight >/dev/null
printf 'net.ipv4.ip_forward=1\n' > "$work_dir/forwarding.conf"
write_file "$work_dir/forwarding.conf" /etc/sysctl.d/99-nids-gateway.conf 0644
sysctl -w net.ipv4.ip_forward=1
iptables-save > "$backup_dir/iptables-before.v4"
if ! iptables -w -n -L NIDS-FORWARD >/dev/null 2>&1; then iptables -w -N NIDS-FORWARD; fi
iptables -w -C FORWARD -j NIDS-FORWARD 2>/dev/null || iptables -w -I FORWARD 1 -j NIDS-FORWARD
iptables -w -C NIDS-FORWARD -i "$internal_if" -o "$external_if" -s "$client_subnet" -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || iptables -w -A NIDS-FORWARD -i "$internal_if" -o "$external_if" -s "$client_subnet" -m conntrack --ctstate NEW,ESTABLISHED,RELATED -j ACCEPT
iptables -w -C NIDS-FORWARD -i "$external_if" -o "$internal_if" -d "$client_subnet" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || iptables -w -A NIDS-FORWARD -i "$external_if" -o "$internal_if" -d "$client_subnet" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -w -t nat -C POSTROUTING -s "$client_subnet" -o "$external_if" -j MASQUERADE 2>/dev/null || iptables -w -t nat -A POSTROUTING -s "$client_subnet" -o "$external_if" -j MASQUERADE
iptables -w -C INPUT -i "$management_if" -s "$management_subnet" -d "$management_ip" -p tcp --dport "$agent_port" -j ACCEPT 2>/dev/null || iptables -w -I INPUT 1 -i "$management_if" -s "$management_subnet" -d "$management_ip" -p tcp --dport "$agent_port" -j ACCEPT
install -d -m 0755 /etc/iptables
backup_file /etc/iptables/rules.v4
iptables-save > /etc/iptables/rules.v4
chmod 0600 /etc/iptables/rules.v4
systemctl enable netfilter-persistent.service

# -------------------- 2/4: ZEEK INSTALLATION --------------------
stage=zeek-installation
if [[ ! -x "$ZEEK_DIR/bin/zeek" ]]; then
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location "$REPO_URL/Release.key" | gpg --dearmor > "$work_dir/zeek.gpg"
    write_file "$work_dir/zeek.gpg" /usr/share/keyrings/nids-zeek.gpg 0644
    printf 'deb [signed-by=/usr/share/keyrings/nids-zeek.gpg] %s/ /\n' "$REPO_URL" > "$work_dir/zeek.list"
    write_file "$work_dir/zeek.list" /etc/apt/sources.list.d/security-zeek.list 0644
    apt-get update
    apt-get -o DPkg::Lock::Timeout=300 install -y zeek-9.0 zeekctl-9.0
fi
[[ "$("$ZEEK_DIR/bin/zeek" --version 2>&1)" == *'version 9.0.'* ]] || die 'Installed Zeek version is not 9.0.x.'
for path in bin/zeekctl etc/node.cfg share/zeek/site/local.zeek share/zeekctl/scripts/post-terminate share/zeekctl/scripts/archive-log; do
    [[ -f "$ZEEK_DIR/$path" ]] || die "Required Zeek file is absent: $path"
done
if systemctl is-active --quiet zeek.service; then systemctl stop zeek.service; fi
if pgrep -x zeek >/dev/null; then die 'A Zeek process remains outside the stopped service; inspect it manually.'; fi
backup_file "$ZEEK_DIR/etc/node.cfg"
python3 - "$ZEEK_DIR/etc/node.cfg" "$internal_if" <<'PY'
import configparser
import sys
config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=('#', ';'))
config.read(sys.argv[1])
if config.sections() != ['zeek'] or config['zeek'].get('type', '').strip() != 'standalone' or config['zeek'].get('host', '').strip() not in ('localhost', '127.0.0.1', '::1') or config['zeek'].get('lb_procs', '').strip():
    sys.exit('Expected a single local [zeek] standalone node; configuration was not rewritten.')
config['zeek']['interface'] = sys.argv[2]
with open(sys.argv[1], 'w') as stream:
    config.write(stream)
PY
local_policy="$ZEEK_DIR/share/zeek/site/local.zeek"
if ! grep -Eq '^[[:space:]]*@load[[:space:]]+policy/tuning/json-logs(\.zeek)?[[:space:]]*$' "$local_policy"; then
    backup_file "$local_policy"
    printf '\n@load policy/tuning/json-logs\n' >> "$local_policy"
fi
getent group zeek >/dev/null || groupadd --system zeek
usermod -a -G zeek "$agent_user"
"$ZEEK_DIR/bin/zeekctl" check
# Unlike deploy, install does not launch an unmanaged capture process.
"$ZEEK_DIR/bin/zeekctl" install
install -d -m 2750 -g zeek "$ZEEK_DIR/logs" "$ZEEK_DIR/spool"
chgrp -R zeek "$ZEEK_DIR/logs" "$ZEEK_DIR/spool"
chmod -R g+rX,g-w,o-rwx "$ZEEK_DIR/logs" "$ZEEK_DIR/spool"
find "$ZEEK_DIR/logs" "$ZEEK_DIR/spool" -type d -exec chmod g+s {} +
setfacl -m g:zeek:--x "$ZEEK_DIR"
find "$ZEEK_DIR/logs" "$ZEEK_DIR/spool" -type d -exec setfacl -m d:u::rwx,d:g::r-x,d:g:zeek:r-x,d:m::r-x,d:o::--- {} +

# -------------------- 3/4: ZEEK AUTOSTART AND CAPTURE --------------------
stage=zeek-autostart
cat > "$work_dir/capture" <<'CAPTURE'
#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CAPTURE
printf 'readonly INTERFACE=%q\n' "$internal_if" >> "$work_dir/capture"
cat >> "$work_dir/capture" <<'CAPTURE'
[[ $EUID -eq 0 && -d /sys/class/net/$INTERFACE ]] || { echo 'Root and the capture interface are required.' >&2; exit 1; }
ethtool -K "$INTERFACE" tx off tso off gso off gro off lro off
features="$(ethtool -k "$INTERFACE")"
python3 - "$features" <<'PY'
import sys
features = {line.split(': ', 1)[0]: line.split(': ', 1)[1].split()[0]
    for line in sys.argv[1].splitlines() if line and not line[0].isspace() and ': ' in line}
required = ('tx-checksumming', 'tcp-segmentation-offload', 'generic-segmentation-offload', 'generic-receive-offload', 'large-receive-offload')
invalid = {name: features.get(name, 'not reported') for name in required if features.get(name) != 'off'}
if invalid:
    sys.exit(f'Capture offload verification failed: {invalid}')
print('Capture offloads verified off; Zeek checksum validation unchanged.')
PY
CAPTURE
write_file "$work_dir/capture" "$CAPTURE_HELPER" 0755
device_unit="$(systemd-escape --path --suffix=device "/sys/subsystem/net/devices/$internal_if")"
cat > "$work_dir/zeek.service" <<EOF
[Unit]
Description=Zeek standalone network monitor managed by ZeekControl
Wants=network-online.target
Requires=$device_unit
After=network-online.target $device_unit

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
Group=zeek
UMask=0027
WorkingDirectory=/opt/zeek
Environment=PATH=/opt/zeek/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStartPre=$CAPTURE_HELPER
ExecStart=/opt/zeek/bin/zeekctl start
ExecStop=/opt/zeek/bin/zeekctl stop
ExecStop=/usr/bin/timeout 120 /bin/sh -c 'while /usr/bin/pgrep -f "[ /]/opt/zeek/share/zeekctl/scripts/(post-terminate|archive-log)" >/dev/null; do /usr/bin/sleep 1; done'
TimeoutStartSec=180
TimeoutStopSec=180
KillMode=control-group

[Install]
WantedBy=multi-user.target
EOF
systemd-analyze verify "$work_dir/zeek.service"
write_file "$work_dir/zeek.service" /etc/systemd/system/zeek.service 0644
systemctl daemon-reload
systemctl enable zeek.service
systemctl start zeek.service
systemctl is-active --quiet zeek.service || die 'Zeek service is not active.'
status_output="$("$ZEEK_DIR/bin/zeekctl" status)"
service_cgroup="$(systemctl show zeek.service -p ControlGroup --value)"
python3 - "$status_output" "$service_cgroup" "$internal_if" <<'PY'
import os
from pathlib import Path
import sys
rows = [line.split() for line in sys.argv[1].splitlines() if line.split()[:1] == ['zeek']]
if len(rows) != 1 or len(rows[0]) < 5 or rows[0][1] != 'standalone' or rows[0][3] != 'running' or not rows[0][4].isdigit():
    sys.exit('ZeekControl did not report the running standalone node.')
process = Path('/proc') / rows[0][4]
group = sys.argv[2]
if not group or group == '/' or os.path.realpath(process / 'exe') != os.path.realpath('/opt/zeek/bin/zeek'):
    sys.exit('Zeek executable/service ownership verification failed.')
memberships = [line.split(':', 2)[2] for line in (process / 'cgroup').read_text().splitlines() if line.startswith('0::')]
if len(memberships) != 1 or not (memberships[0] == group or memberships[0].startswith(group + '/')):
    sys.exit('Zeek is not owned by zeek.service.')
arguments = (process / 'cmdline').read_bytes().split(b'\0')
if not any(arguments[i:i+2] == [b'-i', sys.argv[3].encode()] for i in range(len(arguments)-1)):
    sys.exit('Zeek is capturing on the wrong interface.')
print(f'Verified managed standalone Zeek PID {rows[0][4]}.')
PY

# -------------------- 4/4: SENSOR ENVIRONMENT AND AUTOSTART --------------------
stage=sensor-autostart
install -d -o root -g root -m 0755 "$AGENT_DIR"
write_file "$SOURCE_DIR/collector.py" "$AGENT_DIR/collector.py" 0644
install -d -o root -g root -m 0755 /usr/local/libexec
write_file "$SOURCE_DIR/reset_logs.py" "$RESET_HELPER" 0755
write_file "$SOURCE_DIR/requirements.txt" "$AGENT_DIR/requirements.txt" 0644
(
    umask 022
    [[ -x "$AGENT_DIR/.venv/bin/python" ]] || python3 -m venv "$AGENT_DIR/.venv"
    "$AGENT_DIR/.venv/bin/python" -m pip --disable-pip-version-check install --require-virtualenv -r "$AGENT_DIR/requirements.txt"
)
"$AGENT_DIR/.venv/bin/python" - "$env_source" "$work_dir/agent.env" "$management_ip" "$agent_port" <<'PY'
from dotenv import dotenv_values
from pathlib import Path
import re
import secrets
import sys

required = ('API_KEY', 'AGENT_HOST', 'AGENT_PORT', 'ZEEK_LOG_DIR', 'MAX_BATCH_RECORDS', 'MAX_BATCH_BYTES', 'MAX_LINE_BYTES')
if sys.argv[1]:
    values = dotenv_values(sys.argv[1], encoding='utf-8-sig')
    if any(not values.get(key) for key in required):
        sys.exit('Existing sensor .env is missing required settings; its secret was not replaced.')
else:
    values = dict(API_KEY=secrets.token_hex(32), ZEEK_LOG_DIR='/opt/zeek/logs', MAX_BATCH_RECORDS='500', MAX_BATCH_BYTES='4194304', MAX_LINE_BYTES='1048576')
if not re.fullmatch(r'[A-Za-z0-9._~-]{32,256}', values['API_KEY']) or values['API_KEY'].startswith('REPLACE_'):
    sys.exit('API_KEY must be a real 32-256 character URL-safe secret, not the example placeholder.')
if values['ZEEK_LOG_DIR'] != '/opt/zeek/logs':
    sys.exit('This setup supports only /opt/zeek/logs; existing configuration was not silently remapped.')
values['AGENT_HOST'], values['AGENT_PORT'] = sys.argv[3:5]
for key in ('MAX_BATCH_RECORDS', 'MAX_BATCH_BYTES', 'MAX_LINE_BYTES'):
    if not re.fullmatch(r'[0-9]+', str(values[key])):
        sys.exit(f'{key} must be a positive integer')
records, size, line = (int(values[key]) for key in ('MAX_BATCH_RECORDS', 'MAX_BATCH_BYTES', 'MAX_LINE_BYTES'))
if not (500 <= records <= 1000 and 1024 <= size <= 16*1024*1024 and 1024 <= line <= size):
    sys.exit('Sensor request limits are invalid or incompatible with backend batches of 500.')
Path(sys.argv[2]).write_text(''.join(f'{key}={values[key]}\n' for key in required))
PY
if [[ ! -f "$AGENT_DIR/.env" ]] || ! cmp -s "$work_dir/agent.env" "$AGENT_DIR/.env"; then backup_file "$AGENT_DIR/.env"; fi
install -o "$agent_user" -g "$(id -gn "$agent_user")" -m 0600 "$work_dir/agent.env" "$AGENT_DIR/.env"
"$AGENT_DIR/.venv/bin/python" "$SOURCE_DIR/provision_tls.py" --directory "$AGENT_DIR/tls" --host "$management_ip"
chown root:"$(id -gn "$agent_user")" "$AGENT_DIR/tls" "$AGENT_DIR/tls/server.key" "$AGENT_DIR/tls/server.crt" "$AGENT_DIR/tls/ca.crt"
chmod 0750 "$AGENT_DIR/tls"
chmod 0640 "$AGENT_DIR/tls/server.key"
chmod 0644 "$AGENT_DIR/tls/server.crt" "$AGENT_DIR/tls/ca.crt"
printf 'TLS_CERT_FILE=%s/tls/server.crt\nTLS_KEY_FILE=%s/tls/server.key\n' "$AGENT_DIR" "$AGENT_DIR" >> "$AGENT_DIR/.env"
# Run the import/configuration/log-read check as the actual service account.
runuser -u "$agent_user" -g "$(id -gn "$agent_user")" -G zeek -- env -i PATH="$PATH" LANG=C.UTF-8 "$AGENT_DIR/.venv/bin/python" - "$AGENT_DIR/collector.py" <<'PY'
import os
from pathlib import Path
import runpy
import gzip
import sys
os.chdir(Path(sys.argv[1]).parent)
module = runpy.run_path(sys.argv[1], run_name='nids_setup_preflight')
def fail(error):
    raise error
for root in (module['LOG_DIR'], module['CURRENT_LOG_DIR']):
    for directory, _, names in os.walk(root, onerror=fail):
        for name in names:
            if name == 'conn.log' or (name.startswith('conn.') and name.endswith(('.log', '.log.gz'))):
                path = Path(directory)/name
                opener = gzip.open if name.endswith('.gz') else open
                with opener(path, 'rb') as stream:
                    first = stream.readline(module['MAX_LINE_BYTES'] + 1)
                if first.startswith(b'#'):
                    sys.exit('Existing connection logs use legacy TSV. Keep them separately or convert them before enabling the JSON collector; no old log was deleted.')
                if len(first) > module['MAX_LINE_BYTES']:
                    sys.exit('A connection record exceeds the configured line budget.')
                if first and not first.endswith(b'\n') and root == module['LOG_DIR']:
                    sys.exit('An archived connection log has an incomplete first record.')
                if first.endswith(b'\n'):
                    module['parse_record'](first)
print('Sensor configuration and log/archive permissions verified as the service user.')
PY
sed "s/@AGENT_UID@/$(id -u "$agent_user")/g" "$SOURCE_DIR/nids-reset.service" > "$work_dir/nids-reset.service"
systemd-analyze verify "$work_dir/nids-reset.service"
write_file "$work_dir/nids-reset.service" /etc/systemd/system/nids-reset.service 0644
cat > "$work_dir/nids-sensor.service" <<EOF
[Unit]
Description=AI NIDS Zeek log reader
Wants=network-online.target zeek.service nids-reset.service
After=network-online.target zeek.service nids-reset.service

[Service]
Type=simple
User=$agent_user
SupplementaryGroups=zeek
WorkingDirectory=$AGENT_DIR
Environment=AGENT_HOST=$management_ip
ExecStart=$AGENT_DIR/.venv/bin/python $AGENT_DIR/collector.py
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF
systemd-analyze verify "$work_dir/nids-sensor.service"
write_file "$work_dir/nids-sensor.service" /etc/systemd/system/nids-sensor.service 0644
systemctl daemon-reload
systemctl enable nids-reset.service
systemctl restart nids-reset.service
systemctl enable nids-sensor.service
systemctl restart nids-sensor.service
runuser -u "$agent_user" -g "$(id -gn "$agent_user")" -G zeek -- "$AGENT_DIR/.venv/bin/python" - "$AGENT_DIR/.env" "$management_ip" "$agent_port" <<'PY'
from dotenv import dotenv_values
import json
import sys
import time
import urllib.request
import ssl
config = dotenv_values(sys.argv[1])
request = urllib.request.Request(f'https://{sys.argv[2]}:{sys.argv[3]}/health', headers={'X-API-Key': config['API_KEY']})
context = ssl.create_default_context(cafile=str(__import__('pathlib').Path(sys.argv[1]).parent / 'tls/ca.crt'))
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
for attempt in range(20):
    try:
        with opener.open(request, timeout=2) as response:
            body = json.load(response)
        if body.get('status') != 'ok' or body.get('service') != 'zeek-sensor-agent':
            raise ValueError('Unexpected sensor health response')
        break
    except Exception:
        if attempt == 19:
            sys.exit('Authenticated sensor health failed. Inspect journalctl -u nids-sensor.service; an unmanaged process may occupy the port.')
        time.sleep(1)
PY
for unit in zeek.service nids-sensor.service netfilter-persistent.service; do
    systemctl is-enabled --quiet "$unit" || die "$unit is not enabled at boot."
done
systemctl is-active --quiet nids-sensor.service || die 'Sensor service exited after startup.'
printf '\nSUCCESS: Ubuntu gateway, Zeek and sensor setup completed. No reboot was issued.\n'
printf 'Backups: %s\nSensor configuration/key: %s/.env (not printed)\n' "$backup_dir" "$AGENT_DIR"
printf 'Backend settings: SENSOR_MOCK_MODE=False; SENSOR_AGENT_URL=https://%s:%s\n' "$management_ip" "$agent_port"
printf 'Copy API_KEY from the protected sensor .env to backend SENSOR_AGENT_API_KEY.\n'
printf 'Windows client: use an address in %s, gateway %s and an explicit reachable DNS server.\n' "$client_subnet" "${internal_cidr%/*}"
printf 'After reboot: sudo systemctl status zeek nids-sensor --no-pager\n'
printf '  sudo /opt/zeek/bin/zeekctl status\n  sudo ethtool -k %s\n' "$internal_if"
printf 'Zeek oneshot startup does not continuously monitor/restart a later capture crash.\n'
printf 'Copy public tls/ca.crt to the host and set SENSOR_CA_CERT to its path. Never copy private keys.\n'
