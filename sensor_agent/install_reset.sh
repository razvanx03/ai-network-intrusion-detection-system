#!/usr/bin/env bash
# Update only the existing collector and install its restricted reset broker.
# Installation never invokes a reset or deletes captured logs.
set -Eeuo pipefail
umask 077
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
[[ $EUID -eq 0 ]] || { printf 'Run with sudo bash sensor_agent/install_reset.sh\n' >&2; exit 1; }
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
agent_user="$(systemctl show nids-sensor.service -p User --value)"
agent_dir="$(systemctl show nids-sensor.service -p WorkingDirectory --value)"
[[ -n "$agent_user" && "$agent_user" != root && "$agent_user" != *[!A-Za-z0-9_-]* ]] || { printf 'Expected an existing non-root sensor service user.\n' >&2; exit 1; }
agent_uid="$(id -u "$agent_user")"
[[ "$agent_uid" -gt 0 && "$agent_dir" = /* && -d "$agent_dir" && ! -L "$agent_dir" ]] || exit 1
[[ -f "$agent_dir/.env" && -x "$agent_dir/.venv/bin/python" ]] || { printf 'Unsupported collector installation. No configuration was changed.\n' >&2; exit 1; }
agent_exec="$(systemctl show nids-sensor.service -p ExecStart --value)"
if [[ "$agent_exec" == *"$agent_dir/collector.py"* ]]; then
    agent_script="$agent_dir/collector.py"
elif [[ "$agent_exec" == *"$agent_dir/sensor_agent.py"* ]]; then
    agent_script="$agent_dir/sensor_agent.py"
else
    printf 'Unsupported sensor command. No service was changed.\n' >&2; exit 1
fi
[[ -f "$agent_script" && ! -L "$agent_script" ]] || exit 1
[[ -d /opt/zeek/logs && -d /opt/zeek/spool/zeek && ! -L /opt/zeek/logs && ! -L /opt/zeek/spool/zeek ]] || exit 1
[[ ! -L /usr/local/libexec/nids-reset-logs.py && ! -L /etc/systemd/system/nids-reset.service ]] || exit 1
for file in collector.py reset_logs.py nids-reset.service; do [[ -f "$source_dir/$file" ]] || exit 1; done
[[ -z "$(systemctl show nids-reset.service -p DropInPaths --value)" ]] || { printf 'Review reset service overrides before updating.\n' >&2; exit 1; }
temporary="$(mktemp --suffix=.service /tmp/nids-reset-service.XXXXXXXX)"
trap 'rm -f -- "$temporary"' EXIT
sed "s/@AGENT_UID@/$agent_uid/g" "$source_dir/nids-reset.service" > "$temporary"
systemd-analyze verify "$temporary"
backup_dir="$(mktemp -d /var/backups/nids-reset-install.XXXXXXXX)"
cp -p -- "$agent_script" "$backup_dir/collector.py"
for file in /etc/systemd/system/nids-reset.service /usr/local/libexec/nids-reset-logs.py; do
    if [[ -f "$file" ]]; then cp -p -- "$file" "$backup_dir/"; fi
done
install -d -o root -g root -m 0755 /usr/local/libexec
install -o root -g root -m 0755 "$source_dir/reset_logs.py" /usr/local/libexec/nids-reset-logs.py
install -o root -g root -m 0644 "$temporary" /etc/systemd/system/nids-reset.service
install -o root -g root -m 0644 "$source_dir/collector.py" "$agent_script"
systemctl daemon-reload
systemctl enable nids-reset.service
systemctl restart nids-reset.service
systemctl restart nids-sensor.service
systemctl is-active --quiet nids-reset.service
systemctl is-active --quiet nids-sensor.service
printf 'Reset support installed. Logs were not deleted. Backups: %s\n' "$backup_dir"
