#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
    echo "Usage: bash install_zeek.sh <capture-interface>" >&2
    exit 1
fi
CAPTURE_INTERFACE="$1"
[[ "$CAPTURE_INTERFACE" =~ ^[a-zA-Z0-9_.:-]+$ ]] || exit 1
ip link show dev "$CAPTURE_INTERFACE" >/dev/null
source /etc/os-release
if [[ "$ID" != ubuntu || ! "$VERSION_ID" =~ ^(22.04|24.04)$ ]]; then
    echo "Supported: Ubuntu 22.04/24.04. Install Zeek manually on other distributions." >&2
    exit 1
fi
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="https://download.opensuse.org/repositories/security:/zeek/xUbuntu_${VERSION_ID}"
sudo apt-get update
sudo apt-get install -y curl gpg ca-certificates python3 python3-venv
KEY_FILE="$(mktemp)"
trap 'rm -f -- "$KEY_FILE"' EXIT
curl --fail --silent --show-error --location "$REPO_URL/Release.key" | gpg --dearmor > "$KEY_FILE"
sudo install -m 0644 "$KEY_FILE" /usr/share/keyrings/nids-zeek.gpg
printf 'deb [signed-by=/usr/share/keyrings/nids-zeek.gpg] %s/ /\n' "$REPO_URL" | sudo tee /etc/apt/sources.list.d/security-zeek.list >/dev/null
sudo apt-get update
sudo apt-get install -y zeek
NODE_CONFIG=/opt/zeek/etc/node.cfg
LOCAL_POLICY=/opt/zeek/share/zeek/site/local.zeek
[[ -f "$NODE_CONFIG" && -f "$LOCAL_POLICY" ]] || { echo "Missing Zeek configuration" >&2; exit 1; }
[[ "$(grep -Ec '^[[:space:]]*type[[:space:]]*=[[:space:]]*standalone[[:space:]]*$' "$NODE_CONFIG")" == 1 ]] || { echo "Configure cluster interfaces manually" >&2; exit 1; }
sudo sed -i -E "s/^[[:space:]]*interface[[:space:]]*=.*/interface=$CAPTURE_INTERFACE/" "$NODE_CONFIG"
grep -Fx "interface=$CAPTURE_INTERFACE" "$NODE_CONFIG"
if ! grep -Eq '^[[:space:]]*@load policy/tuning/json-logs(\.zeek)?[[:space:]]*$' "$LOCAL_POLICY"; then
    printf '\n@load policy/tuning/json-logs\n' | sudo tee -a "$LOCAL_POLICY" >/dev/null
fi
sudo /opt/zeek/bin/zeekctl check
sudo /opt/zeek/bin/zeekctl deploy
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    (umask 077; cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env")
fi
echo "Configure .env, state ownership and log-read permissions using README.md before starting the sensor."
