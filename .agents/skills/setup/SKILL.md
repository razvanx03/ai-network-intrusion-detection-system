---
name: setup
description: Configure or repair the AI NIDS Ubuntu sensor VM using sensor_agent/setup_vm.sh, including gateway networking, Zeek capture and the Python collector, and report verified results and repairs. Use when asked to set up this project's Linux VM.
---

# Ubuntu sensor setup

Run the repository's maintained installer on the intended Ubuntu VM, diagnose setup
failures within that scope, and finish with evidence of what works. Creating or
reading this skill alone does not authorize running the installer. An invocation
requesting VM setup authorizes its gateway, Zeek and sensor changes.

## Discover and prepare

- Locate this project's repository from the current workspace; read its `AGENTS.md`,
  `sensor_agent/README.md`, `sensor_agent/setup_vm.sh`, `collector.py` and
  `requirements.txt`. These files are the current implementation, not the removed
  individual gateway/Zeek/autostart helpers. Never install the main backend or its
  database on the sensor: only the collector runs there.
- Identify the requested VM and available access. Prefer SSH or VirtualBox guest
  control over desktop automation. Use existing authorized authentication without
  embedding credentials in this skill, source files, reports or command transcripts.
  If the target or authentication cannot be established, request only what is missing.
- Inspect Ubuntu version, disk space, interfaces, routes, active network renderer,
  firewall managers, existing Zeek/agent services and their installation paths.
  Map NAT, internal client LAN and host-only management by evidence; do not infer
  their roles from interface order alone. Discover the existing management address.
  The installer requires Ubuntu 24.04, three distinct adapters, a non-root service
  account and an already assigned management IPv4 address.
- If VirtualBox adapters are missing, identify the required change. Do not create
  host adapters or change the host/Windows client's network configuration under a
  Linux-VM setup request. Obtain the user's direction for those external prerequisites.
- Preserve existing agent credentials, retained logs and backend ingestion progress.
  For a legacy installation, identify its protected `.env` and pass `--env-file`;
  do not lose the key by generating a second one. Never print the key.

## Apply the maintained installer

1. Copy `setup_vm.sh`, `collector.py` and `requirements.txt` together into a dedicated
   directory inside the VM. Transfer an existing `.env` only through the authorized
   secure channel when needed; restrict its permissions. Verify the transferred
   source hashes and LF line endings. Use fresh destinations when copying logs back:
   some VirtualBox copy operations may leave trailing bytes in an existing file.
2. Run `bash -n setup_vm.sh`, then the root preflight with the discovered values:

   ```bash
   sudo bash setup_vm.sh --management-ip <actual-ip> --agent-user <actual-user> --check
   ```

   Supply `--external-if`, `--internal-if`, `--management-if`, `--internal-cidr`,
   `--agent-port` and `--env-file` when the inspected configuration requires them.
   Do not use example IPs as silently assumed configuration.
3. Run the same command without `--check` through the VM console or another channel
   that survives a networking change. Preserve the installer's root-only backups.
   Capture the exit status and failed stage without exposing credentials.
4. Diagnose errors using the failed command, service logs and actual VM state.
   Repair routine, local setup problems such as file permissions, missing declared
   dependencies, a wrong interface argument or conflicting legacy service paths.
   If the maintained installer is defective, make a minimal reusable correction in
   the repository, validate Bash/Python as appropriate, transfer it and retry.
   Record each failure, its cause, the correction and the new verification result.
5. Do not bypass a failed check, disable unrelated firewalls, flush firewall rules,
   replace the network renderer, weaken authentication, run the collector as root,
   delete logs/databases, or repeatedly reinstall packages without diagnosing the
   error. Do not change the host or unrelated VM applications. If the same failure
   survives two targeted repairs, stop that stage with its evidence and next action
   instead of an unbounded retry loop. Continue independent read-only verification.

The installer already manages gateway/NAT, standalone Zeek 9.0 JSON capture,
capture offloads, log access and both systemd services. Do not duplicate those
implementations or start an unmanaged `zeek -i` / `zeekctl deploy` alongside systemd.
Do not reboot automatically unless the invocation also authorizes a reboot test.
Do not stage, commit or push changes.

## Verify and report

- Verify the actual installed unit definitions and enabled/active state of
  `zeek.service` and `nids-sensor.service`. Run `/opt/zeek/bin/zeekctl status` and
  confirm a real capture PID bound to the monitored interface. `active (exited)`
  on the Zeek oneshot service does not prove capture is healthy.
- Verify IPv4 forwarding, the client gateway address, the NAT/default route and
  persistent scoped firewall rules. Check the capture helper's offload settings
  with `ethtool -k` while keeping Zeek checksum validation enabled.
- Query authenticated sensor `/health`, `/files` and a bounded, read-only `/logs`
  request using the protected key without logging it. Verify readability of current
  and retained archived `conn.log` streams when present. A health response alone
  does not establish live packet capture or archive ingestion.
- When an authorized Windows client is available, use a small benign traffic probe
  and identify its new Zeek connection record. Do not generate attacks. If the client
  is unavailable, mark traffic validation untested, not successful.
- When a running host backend is available, verify reachability without changing
  its `.env` or importing/analyzing records unless the user requested that too.
  Report the sensor URL and whether its existing backend key matches without
  revealing the key. State any required host configuration as a pending action.
- Keep graphical desktop repairs separate from gateway configuration. This VM has
  previously encountered a GNOME/Xorg/VirtualBox login rendering race; do not
  undo its Wayland/software-cursor configuration during a network setup.

Finish in the user's language with: target VM and installed paths; completed
stages; checks passed and checks not performed; each encountered error and how it
was repaired; unresolved failures and required next actions; service autostart
status and backup location. If no errors occurred, say so explicitly. Never claim
the complete data flow or reboot persistence was tested unless it actually was.
