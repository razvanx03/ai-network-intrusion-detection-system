#!/usr/bin/env bash
# ==============================================================================
# One-Shot Zeek & Sensor Agent Setup Script for Ubuntu/Debian VMs
# Configures network interface, enables JSON logging, deploys Zeek,
# and sets up the Python agent environment automatically.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/6] Detecting System & Network Interface ==="
# Detect active default interface (e.g. enp0s3 in VirtualBox, ens33 in VMware, eth0)
ACTIVE_IFACE=$(ip -o -4 route show to default | awk '{print $5}' | head -n1)
if [ -z "$ACTIVE_IFACE" ]; then
    ACTIVE_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v 'lo' | head -n1)
fi
echo "Target sniffing interface detected: ${ACTIVE_IFACE}"

echo "=== [2/6] Installing Prerequisites ==="
sudo apt-get update -y
sudo apt-get install -y curl gnupg2 software-properties-common python3 python3-pip python3-venv libpcap-dev net-tools

echo "=== [3/6] Installing Zeek Network Security Monitor ==="
UBUNTU_CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")

# Add official Zeek repository from OpenSUSE build service
REPO_FILE="/etc/apt/sources.list.d/security:zeek.list"
echo "deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_${UBUNTU_CODENAME}/ /" | sudo tee "$REPO_FILE"
curl -fsSL "https://download.opensuse.org/repositories/security:/zeek/xUbuntu_${UBUNTU_CODENAME}/Release.key" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/security_zeek.gpg > /dev/null

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y zeek || sudo apt-get install -y zeek-core zeekctl

# Export Zeek binary paths
export PATH="/opt/zeek/bin:/usr/local/zeek/bin:$PATH"

echo "=== [4/6] Configuring Zeek (Interface & Native JSON Output) ==="
# Locate Zeek configuration files
NODE_CFG="/opt/zeek/etc/node.cfg"
[ ! -f "$NODE_CFG" ] && NODE_CFG="/etc/zeek/node.cfg"
[ ! -f "$NODE_CFG" ] && NODE_CFG="/usr/local/zeek/etc/node.cfg"

if [ -f "$NODE_CFG" ]; then
    echo "Updating sniffing interface in ${NODE_CFG} to ${ACTIVE_IFACE}..."
    sudo sed -i "s/interface=.*/interface=${ACTIVE_IFACE}/g" "$NODE_CFG"
fi

SITE_LOCAL="/opt/zeek/share/zeek/site/local.zeek"
[ ! -f "$SITE_LOCAL" ] && SITE_LOCAL="/usr/share/zeek/site/local.zeek"
[ ! -f "$SITE_LOCAL" ] && SITE_LOCAL="/usr/local/zeek/share/zeek/site/local.zeek"

if [ -f "$SITE_LOCAL" ]; then
    if ! grep -q "json-logs.zeek" "$SITE_LOCAL"; then
        echo "@load policy/tuning/json-logs.zeek" | sudo tee -a "$SITE_LOCAL"
        echo "Enabled native JSON logging in ${SITE_LOCAL}."
    fi
fi

# Ensure log directory structure exists
sudo mkdir -p /opt/zeek/logs/current
sudo chmod -R 755 /opt/zeek/logs

echo "=== [5/6] Deploying & Starting Zeek Service ==="
if command -v /opt/zeek/bin/zeekctl >/dev/null 2>&1; then
    sudo /opt/zeek/bin/zeekctl check
    sudo /opt/zeek/bin/zeekctl deploy || sudo /opt/zeek/bin/zeekctl start
    echo "Zeek successfully deployed via zeekctl."
elif command -v zeekctl >/dev/null 2>&1; then
    sudo zeekctl check
    sudo zeekctl deploy || sudo zeekctl start
    echo "Zeek successfully deployed via zeekctl."
else
    echo "Starting standalone Zeek daemon sniffing ${ACTIVE_IFACE}..."
    sudo pkill -f "zeek -i" || true
    nohup sudo zeek -i "$ACTIVE_IFACE" local -b > /opt/zeek/logs/current/zeek.stdout 2>&1 &
fi

echo "=== [6/6] Setting Up Python Agent Environment ==="
cd "$SCRIPT_DIR"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Created Python virtual environment in ${SCRIPT_DIR}/.venv"
fi

"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "Initialized .env configuration in ${SCRIPT_DIR}/.env"
fi

VM_IP=$(ip -4 addr show "$ACTIVE_IFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)

echo ""
echo "=============================================================================="
echo " [SUCCESS] One-Shot Setup Completed!"
echo "=============================================================================="
echo " - Monitored Interface: ${ACTIVE_IFACE}"
echo " - VM IP Address:        ${VM_IP}"
echo " - Active Log File:     /opt/zeek/logs/current/conn.log"
echo ""
echo "To start the Sensor Collector now, run:"
echo "    cd ${SCRIPT_DIR}"
echo "    ./.venv/bin/python3 collector.py"
echo ""
echo "Or run in background with nohup:"
echo "    nohup ./.venv/bin/python3 collector.py > collector.log 2>&1 &"
echo ""
echo "On your Windows machine (.env), configure:"
echo "    SENSOR_MOCK_MODE=False"
echo "    SENSOR_AGENT_URL=http://${VM_IP}:8000"
echo "=============================================================================="
