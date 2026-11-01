
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Fresh Zeek 9.0 installation for Ubuntu 24.04.
# On failure, report the failed stage and attempt a rollback.

CAPTURE_INTERFACE="${1:-enp0s8}"
REPO_URL="https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04"
REPO_KEY="/usr/share/keyrings/nids-zeek.gpg"
REPO_FILE="/etc/apt/sources.list.d/security-zeek.list"
ZEEK_DIR="/opt/zeek"

STAGE="initialization"
FAILED_COMMAND="unknown"
ROLLING_BACK=0
WORK_DIR="$(mktemp -d)"
BACKUP_DIR="$WORK_DIR/backups"
mkdir -p "$BACKUP_DIR"

dpkg-query -W -f='${binary:Package}\n' 2>/dev/null |
    sort -u > "$WORK_DIR/packages.before"

backup_path() {
    local path="$1"
    local name="$2"

    if sudo test -e "$path" || sudo test -L "$path"; then
        sudo cp -a "$path" "$BACKUP_DIR/$name"
        echo yes > "$BACKUP_DIR/$name.existed"
    else
        echo no > "$BACKUP_DIR/$name.existed"
    fi
}

restore_path() {
    local path="$1"
    local name="$2"

    [[ -f "$BACKUP_DIR/$name.existed" ]] || return 0

    if [[ "$(cat "$BACKUP_DIR/$name.existed")" == "yes" ]]; then
        sudo rm -f -- "$path"
        sudo cp -a "$BACKUP_DIR/$name" "$path"
    else
        sudo rm -f -- "$path"
    fi
}

rollback() {
    local exit_code="$1"
    local line="$2"
    local package_list="$WORK_DIR/new-packages"

    (( ROLLING_BACK == 1 )) && exit "$exit_code"
    ROLLING_BACK=1
    trap - ERR
    set +e

    echo >&2
    echo "ERROR: Installation failed." >&2
    echo "Stage: $STAGE" >&2
    echo "Line: $line" >&2
    echo "Command: $FAILED_COMMAND" >&2
    echo "Exit code: $exit_code" >&2
    echo "Starting rollback..." >&2

    dpkg-query -W -f='${binary:Package}\n' 2>/dev/null |
        sort -u > "$WORK_DIR/packages.after"

    comm -13 "$WORK_DIR/packages.before" "$WORK_DIR/packages.after" |
        grep -E '^(zeek|libbroker)' > "$package_list" || true

    if [[ -s "$package_list" ]]; then
        mapfile -t packages < "$package_list"
        echo "Removing packages newly installed by this run..." >&2
        sudo apt-get purge -y "${packages[@]}"
        if [[ $? -ne 0 ]]; then
            echo "WARNING: Some packages could not be removed." >&2
        fi
    fi

    restore_path "$REPO_FILE" repo
    restore_path "$REPO_KEY" key
    restore_path "/usr/local/bin/zeek" zeek-link
    restore_path "/usr/local/bin/zeekctl" zeekctl-link

    if sudo test -e "$ZEEK_DIR"; then
        echo "WARNING: $ZEEK_DIR remains. Inspect it manually; it was not deleted." >&2
    fi

    sudo apt-get update
    echo "Rollback attempt finished. Review any warnings above." >&2
    rm -rf "$WORK_DIR"
    exit "$exit_code"
}

on_error() {
    local exit_code="$1"
    local line="$2"
    FAILED_COMMAND="${BASH_COMMAND:-unknown}"
    rollback "$exit_code" "$line"
}

trap 'on_error "$?" "$LINENO"' ERR

if [[ $EUID -eq 0 ]]; then
    echo "ERROR: Run this script as a regular user, without sudo." >&2
    exit 1
fi

if [[ ! "$CAPTURE_INTERFACE" =~ ^[a-zA-Z0-9_.:-]+$ ]]; then
    echo "ERROR: Invalid interface name: $CAPTURE_INTERFACE" >&2
    exit 1
fi

if ! ip link show dev "$CAPTURE_INTERFACE" >/dev/null 2>&1; then
    echo "ERROR: Network interface '$CAPTURE_INTERFACE' does not exist." >&2
    exit 1
fi

source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != "24.04" ]]; then
    echo "ERROR: This script supports Ubuntu 24.04 only." >&2
    exit 1
fi

if sudo test -e "$ZEEK_DIR"; then
    echo "ERROR: $ZEEK_DIR already exists. Inspect it before proceeding." >&2
    exit 1
fi

# Refuse to overwrite an existing Zeek repository definition.
if sudo test -e "$REPO_FILE" && \
   ! sudo grep -Fq "$REPO_URL" "$REPO_FILE"; then
    echo "ERROR: $REPO_FILE contains a different repository definition." >&2
    exit 1
fi

backup_path "$REPO_FILE" repo
backup_path "$REPO_KEY" key
backup_path /usr/local/bin/zeek zeek-link
backup_path /usr/local/bin/zeekctl zeekctl-link

STAGE="installing prerequisites"
echo "[1/5] Installing prerequisites..."
sudo apt-get update
sudo apt-get install -y curl gpg ca-certificates ethtool

STAGE="configuring repository"
echo "[2/5] Configuring the Zeek repository..."
sudo install -d -m 0755 /usr/share/keyrings

curl --fail --silent --show-error --location \
    "$REPO_URL/Release.key" |
    gpg --dearmor > "$WORK_DIR/zeek.gpg"

sudo install -m 0644 "$WORK_DIR/zeek.gpg" "$REPO_KEY"
printf 'deb [signed-by=%s] %s/ /\n' "$REPO_KEY" "$REPO_URL" |
    sudo tee "$REPO_FILE" >/dev/null

sudo apt-get update

STAGE="installing Zeek 9.0"
echo "[3/5] Installing Zeek 9.0 packages..."
sudo apt-get install -y zeek-9.0 zeekctl-9.0

STAGE="checking installed files"
for file in \
    "$ZEEK_DIR/bin/zeek" \
    "$ZEEK_DIR/bin/zeekctl" \
    "$ZEEK_DIR/etc/node.cfg" \
    "$ZEEK_DIR/share/zeek/site/local.zeek"; do
    if ! sudo test -f "$file"; then
        echo "ERROR: Required file not found: $file" >&2
        false
    fi
done

STAGE="configuring Zeek"
echo "[4/5] Configuring Zeek..."

NODE_CONFIG="$ZEEK_DIR/etc/node.cfg"
LOCAL_POLICY="$ZEEK_DIR/share/zeek/site/local.zeek"

if [[ "$(sudo grep -Ec '^[[:space:]]*type[[:space:]]*=[[:space:]]*standalone[[:space:]]*$' "$NODE_CONFIG")" != 1 ]]; then
    echo "ERROR: Expected exactly one standalone node in node.cfg." >&2
    false
fi

if sudo grep -Eq '^[[:space:]]*interface[[:space:]]*=' "$NODE_CONFIG"; then
    sudo sed -i -E \
        "s|^[[:space:]]*interface[[:space:]]*=.*|interface=$CAPTURE_INTERFACE|" \
        "$NODE_CONFIG"
else
    sudo sed -i \
        "/^[[:space:]]*type[[:space:]]*=[[:space:]]*standalone[[:space:]]*$/a interface=$CAPTURE_INTERFACE" \
        "$NODE_CONFIG"
fi

if ! sudo grep -Eq '^[[:space:]]*@load[[:space:]]+policy/tuning/json-logs(\.zeek)?[[:space:]]*$' "$LOCAL_POLICY"; then
    printf '\n@load policy/tuning/json-logs\n' |
        sudo tee -a "$LOCAL_POLICY" >/dev/null
fi

sudo ln -s "$ZEEK_DIR/bin/zeek" /usr/local/bin/zeek
sudo ln -s "$ZEEK_DIR/bin/zeekctl" /usr/local/bin/zeekctl

STAGE="validating and deploying Zeek"
echo "[5/5] Validating and deploying Zeek..."
sudo "$ZEEK_DIR/bin/zeekctl" check
sudo "$ZEEK_DIR/bin/zeekctl" deploy

STAGE="verifying deployment"
sudo "$ZEEK_DIR/bin/zeekctl" status

trap - ERR
rm -rf "$WORK_DIR"

echo
echo "SUCCESS: Zeek installation completed."
echo "Capture interface: $CAPTURE_INTERFACE"
echo "Expected current logs: $ZEEK_DIR/logs/current/"
echo "Expected archived logs: $ZEEK_DIR/logs/"
echo "Verify logs with:"
echo "  sudo ls -lah $ZEEK_DIR/logs/current/"
