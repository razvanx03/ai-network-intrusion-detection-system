#!/usr/bin/env bash
# Manual setup helper for the NIDS Ubuntu gateway VM.
# Expected layout:
#   External/NAT interface: enp0s3
#   Internal/client interface: enp0s8
#   Client subnet: 192.168.50.0/24
#
# Review these values before running on another machine.
# Run with: sudo bash gateway_setup.sh

set -euo pipefail

EXTERNAL_IF="enp0s3"
INTERNAL_IF="enp0s8"
CLIENT_SUBNET="192.168.50.0/24"
SYSCTL_FILE="/etc/sysctl.d/99-nids-gateway.conf"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo: sudo bash $0" >&2
  exit 1
fi

echo "=== NIDS gateway network setup ==="
echo "External interface: ${EXTERNAL_IF}"
echo "Internal interface: ${INTERNAL_IF}"
echo "Client subnet:      ${CLIENT_SUBNET}"
echo
echo "Check that these interface names and the subnet match this VM."
read -r -p "Continue? Type YES to proceed: " confirmation
if [[ "${confirmation}" != "YES" ]]; then
  echo "Cancelled."
  exit 0
fi

for iface in "${EXTERNAL_IF}" "${INTERNAL_IF}"; do
  if ! ip link show "${iface}" >/dev/null 2>&1; then
    echo "ERROR: Interface '${iface}' was not found. No changes made." >&2
    echo "Check interface names with: ip -br addr" >&2
    exit 1
  fi
done

echo
echo "[1/4] Enabling persistent IPv4 forwarding..."
printf 'net.ipv4.ip_forward=1\n' > "${SYSCTL_FILE}"
sysctl --system >/dev/null
sysctl net.ipv4.ip_forward

echo
echo "[2/4] Ensuring iptables-persistent is installed..."
if ! command -v netfilter-persistent >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  DEBIAN_FRONTEND=readline apt-get install -y iptables-persistent
fi

echo
echo "[3/4] Adding NAT rule if it does not already exist..."
if iptables -t nat -C POSTROUTING -s "${CLIENT_SUBNET}" -o "${EXTERNAL_IF}" -j MASQUERADE 2>/dev/null; then
  echo "NAT rule already exists; not adding a duplicate."
else
  iptables -t nat -A POSTROUTING -s "${CLIENT_SUBNET}" -o "${EXTERNAL_IF}" -j MASQUERADE
fi

echo
echo "[4/4] Saving current firewall rules for startup..."
netfilter-persistent save

echo
echo "=== Verification ==="
sysctl net.ipv4.ip_forward
iptables -t nat -S POSTROUTING
echo
echo "Setup complete. Test client internet access before rebooting."
echo "After reboot, repeat the verification commands and test the client again."
echo "This script does not configure Zeek, VM adapters, IP addresses, or routing on the host/router."
