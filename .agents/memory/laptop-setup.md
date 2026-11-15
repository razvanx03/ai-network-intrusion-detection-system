# Fresh laptop setup

Confirmed on 2026-11-15: newly booted Ubuntu 24.04 guests can run unattended
security updates while setup is installing packages. The first local setup
attempt failed at apt install with dpkg's frontend lock held by
unattended-upgrades. The maintained installer now gives both package-install
commands a bounded `DPkg::Lock::Timeout=300`. Never remove locks or interrupt an
updater to make setup pass. An expired wait is still a reported failure; inspect
actual update progress before rerunning.

The five-minute Zeek-package wait expired while automatic updates were still
making progress. Waiting for apt-daily-upgrade.service to finish before retrying
allowed package installation to continue; do not repeatedly contend with it.

## Guest stability and memory adjustment

During this setup, an agent-initiated VirtualBox memory-balloon adjustment caused
a recorded `UBSAN: array-index-out-of-bounds in VBoxGuest-common.c:450:24`, with
`vgdrvBalloonInflate` in the trace. The guest used Ubuntu kernel 7.0.0-42 and
Guest Additions 7.2.4; the host VirtualBox version was 7.2.22. Later the Ubuntu
guest stopped responding to network/Guest Control/heartbeat. The retained journal
does not establish the final freeze's complete cause. The user reported Caps Lock
and Scroll Lock alternation, which stopped after the VM was powered off.

Do not use memory ballooning as a routine resource optimization on this setup.
Both VM balloon settings were restored to zero. The user explicitly requested
leaving Guest Additions unchanged. No Guest Additions update was performed.

After the user authorized forced recovery, Ubuntu was powered off. Its old
VBoxHeadless process remained alive and held its log files, causing subsequent
starts to fail with sharing violations. The exact process was matched to the
VM's recorded PID and parent, and terminated only after its machine state was
confirmed aborted/off. Ubuntu then started with a graphical window, kernel
7.0.0-43 and all three persistent network addresses intact. `dpkg --audit` found
unfinished Zeek dependency configuration; `dpkg --configure -a` completed it and
the subsequent audit was clean. Zeek reported version 9.0.1.

Separately, Windows entered VirtualBox Guru Meditation with
`VINF_EM_TRIPLE_FAULT` after a guest reset during the same run. This evidence does
not establish that it shares Ubuntu's driver failure. Do not change host security
features or infer that a graphical-login fix addresses either failure.

Windows Guest Control authenticated successfully with an administrator account,
but its process token could not run netsh configuration or register a highest-level
scheduled task (elevation required/access denied). A prepared network command
file launched with PowerShell Start-Process -Verb RunAs worked after the user
manually accepted UAC in the VM console. Do not assume account membership makes
Guest Control processes elevated; preserve UAC and request the user's interaction
when necessary. The client then showed its persistent default route through Ubuntu
and successfully pinged both that gateway and an Internet address.

Host verification: selected.joblib matched deployment.json and loaded using the
pinned requirements; 450 existing isolated backend unit tests passed. The initial
frontend production build passed with the existing bundle-size warning. These
checks alone do not establish sensor capture or end-to-end ingestion.

## Completed installation and live verification

The maintained installer subsequently completed successfully, with its final
backup at `/var/backups/nids-vm-setup.BOArzRGT`. Ubuntu runs the collector under
the unprivileged ubuntu account in `/opt/nids-sensor`, Zeek 9.0.1 in `/opt/zeek`,
and the restricted reset broker. The host application uses its new local Python
environment and a freshly initialized SQLite database; no old history was copied.
Only the installation's public CA was transferred through Guest Control to
`certs/sensor-ca.crt`, with equal source/destination SHA256. Private keys stayed
on Ubuntu with the expected root-only CA and restricted server-key permissions.

Verified network roles: NAT on enp0s3, client gateway/capture on enp0s8, management
on enp0s9. The Windows client retained its static address/default route/DNS across
restarts and reached the Internet through Ubuntu. Authenticated sensor HTTPS used
TLS 1.3 with the correct management IP SAN and a server certificate expiring on
2036-11-12. Missing API-key access and untrusted CA access were rejected. Bounded
current and gzip archive reads succeeded with no discovery issues. Reset capability
was supported; no destructive reset was executed.

A normal Ubuntu shutdown/start verified enabled and active Zeek, collector, reset
and firewall persistence. The real post-start Zeek PID captured on enp0s8, required
offloads were off, forwarding was enabled and the scoped NAT rule persisted.
One start showed approximately 193 seconds of guest-clock/heartbeat delay before
recovering; services then started automatically. This is not proof of a repaired
general graphical-login or hypervisor issue. The user explicitly requested
permanent 4096 MB RAM for Ubuntu; that configured allocation and zero ballooning
were verified. Guest Additions and host security features were left unchanged.

After a later continuation both VMs and local servers were still running. Small
Windows ping and HEAD HTTP/HTTPS probes succeeded. The browser showed the exact
example.com probe's HTTP 200, DNS answers and completed TLS 1.3/SNI context.
Ping records with packets in both directions were also imported. Consecutive
completed analyses imported zero additional connections and had no file issues;
read-only database counts equalled distinct UID counts. This verifies live
capture, verified HTTPS ingestion, AI execution, context display and deduplication,
not classifier accuracy. No attack traffic or forced alerts were generated.

Existing non-blocking checks: four backend schema-deprecation warnings, the
frontend bundle-size warning, and npm audit's two low/four moderate advisories in
the shadcn development-tool dependency chain. These dependencies were not changed
as an unrelated security upgrade. Host reboot/server autostart was not tested.
