# Explicit full data reset

User request, 2026-11-14, supersedes the earlier decision to expose archival only:
provide an explicitly confirmed destructive reset in Settings, including Zeek VM
logs. The user initially deferred testing, then explicitly authorized a live reset
test in the same session and accepted starting with no data. This historical test
is not permission to run destructive QA in a future task without authorization.

POST /api/system/reset-data requires the administrator cookie, a 32-hex operation
ID and literal RESET confirmation. A durable system_resets row guards analysis
and archival across requests and backend restarts. Analysis checks this guard
after acquiring its write lock. The VM must acknowledge cleanup and capture
restart before local data is deleted transactionally. Remote errors retain local
data; uncertain outcomes retain the running guard. Resume with the same ID.
Completed operation IDs are retained so retries cannot delete newer data.

The reset clears connections, protocol context, alerts and evidence, sessions and
links, archives/snapshots and sensor cursors. It preserves users, token revocations,
configuration, AI artifacts and reset receipts. Archiving remains reversible and
does not reset cursors or VM logs.

The collector's API-key-protected reset endpoint calls a separate fixed-purpose
root broker over a Unix socket restricted by file permissions and peer UID.
The collector retains its non-root identity and NoNewPrivileges protection.
The broker accepts only a validated operation ID, stops managed Zeek, checks for
remaining capture/rotation processes, removes .log/.log.gz files within the fixed
/opt/zeek/logs and /opt/zeek/spool/zeek roots without following symlinks, then
restarts capture. Durable cleaned/completed receipts avoid purging new captures
when an interrupted request is retried. Configuration and control files stay.

Existing VM installs need the updated sensor_agent files and
sudo bash sensor_agent/install_reset.sh inside Ubuntu. That installer updates
the existing collector path and adds the broker; it never executes a reset.
setup_vm.sh installs the same broker for full installations. Unit checks use
simulated network/process boundaries and synthetic temporary files only.

Authorized live verification, 2026-11-14: updated the existing Ubuntu service at
/home/ubuntu/Desktop/nids_agent/sensor_agent.py through VirtualBox Guest Control.
The updater was adapted to retain that legacy filename. Transferred files had
verified matching SHA-256 hashes and LF endings. Backup:
/var/backups/nids-reset-install.yR9Bp7E1. Agent key, non-root user, NoNewPrivileges,
gateway, AI configuration and administrator were retained. nids-reset, nids-sensor
and zeek were active and enabled afterward; capture had a real new Zeek PID.

The first full reset acknowledged completion, removed 673 old VM log files and
cleared all nine traffic/context/alert/session/archive/cursor tables. A synthetic
single UDP broadcast on the existing internal subnet was captured, imported and
classified in a completed session (one new connection, zero findings). Replaying
the completed reset ID left that newer connection intact. A second authorized
reset removed the probe and 20 generated log files; a read-only DB count showed
all nine tables at zero, one administrator retained, and no pending reset. No
archived gzip logs remained. Capture runs continuously, so fresh traffic and new
automatic sessions can appear afterward. No reboot or model-accuracy test was
performed. ZeekControl's pre-existing optional WebSocket warning remained; it did
not prevent capture, reset or import. The guest temporary credential was deleted
and the protected host temporary credential file was emptied after verification.
