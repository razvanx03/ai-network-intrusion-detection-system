#!/usr/bin/env bash
# Upgrade an existing sensor to verified HTTPS without changing capture or logs.
set -Eeuo pipefail
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run with sudo bash install_https.sh MANAGEMENT_IP [--renew]' >&2; exit 1; }
[[ $# -eq 1 || ( $# -eq 2 && $2 = --renew ) ]] || exit 1
management_ip="$1"
shift
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
agent_user="$(systemctl show nids-sensor.service -p User --value)"
agent_dir="$(systemctl show nids-sensor.service -p WorkingDirectory --value)"
[[ -n "$agent_user" && "$agent_user" != root && "$agent_dir" = /* && -d "$agent_dir" && ! -L "$agent_dir" ]] || exit 1
agent_exec="$(systemctl show nids-sensor.service -p ExecStart --value)"
if [[ "$agent_exec" == *"$agent_dir/collector.py"* ]]; then
    agent_script="$agent_dir/collector.py"
elif [[ "$agent_exec" == *"$agent_dir/sensor_agent.py"* ]]; then
    agent_script="$agent_dir/sensor_agent.py"
else
    echo 'Unsupported sensor service command.' >&2; exit 1
fi
[[ -f "$agent_script" && ! -L "$agent_script" && -f "$agent_dir/.env" && ! -L "$agent_dir/.env" ]] || exit 1
backup="$(mktemp -d /var/backups/nids-https.XXXXXXXX)"
cp -p -- "$agent_script" "$agent_dir/.env" "$backup/"
[[ ! -d "$agent_dir/tls" ]] || cp -a -- "$agent_dir/tls" "$backup/"
(umask 022; "$agent_dir/.venv/bin/python" -m pip --disable-pip-version-check install -r "$source_dir/requirements.txt")
host="$("$agent_dir/.venv/bin/python" - "$management_ip" <<'PY'
import ipaddress, sys
host = str(ipaddress.ip_address(sys.argv[1]))
if ipaddress.ip_address(host).is_unspecified:
    sys.exit('Set AGENT_HOST to the actual management IP before enabling HTTPS.')
print(host)
PY
)"
"$agent_dir/.venv/bin/python" "$source_dir/provision_tls.py" --directory "$agent_dir/tls" --host "$host" "$@"
chown root:"$(id -gn "$agent_user")" "$agent_dir/tls" "$agent_dir/tls/server.key" "$agent_dir/tls/server.crt" "$agent_dir/tls/ca.crt"
chmod 0750 "$agent_dir/tls"
chmod 0640 "$agent_dir/tls/server.key"
chmod 0644 "$agent_dir/tls/server.crt" "$agent_dir/tls/ca.crt"
chown -R root:root "$agent_dir/tls/private"
chmod 0700 "$agent_dir/tls/private"
"$agent_dir/.venv/bin/python" - "$agent_dir/.env" "$agent_dir" "$host" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
lines = [line for line in path.read_text().splitlines() if not line.startswith(('TLS_CERT_FILE=', 'TLS_KEY_FILE=', 'AGENT_HOST='))]
lines += [f'AGENT_HOST={sys.argv[3]}', f'TLS_CERT_FILE={sys.argv[2]}/tls/server.crt', f'TLS_KEY_FILE={sys.argv[2]}/tls/server.key']
path.write_text('\n'.join(lines) + '\n')
PY
install -o root -g root -m 0644 "$source_dir/collector.py" "$agent_script"
systemctl restart nids-sensor.service
sleep 2
systemctl is-active --quiet nids-sensor.service
"$agent_dir/.venv/bin/python" - "$agent_dir" "$host" <<'PY'
import json, ssl, sys, urllib.request
from dotenv import dotenv_values
config = dotenv_values(sys.argv[1] + '/.env')
ctx = ssl.create_default_context(cafile=sys.argv[1] + '/tls/ca.crt')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ctx))
request = urllib.request.Request(f'https://{sys.argv[2]}:{config["AGENT_PORT"]}/health', headers={'X-API-Key': config['API_KEY']})
with opener.open(request, timeout=10) as response:
    assert json.load(response)['status'] == 'ok'
PY
printf 'HTTPS verified. Backup: %s\nCopy only public trust certificate: %s/tls/ca.crt\n' "$backup" "$agent_dir"
