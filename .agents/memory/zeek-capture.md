# Capture and offloading

During the VM traffic investigation, checksum offloading on the Ubuntu capture
interface caused misleading or incomplete observations. The maintained installer
therefore installs a capture helper that disables and checks TX checksum offload,
TSO, GSO, GRO and LRO before Zeek starts. Zeek checksum validation stays enabled.
Inspect `ethtool -k` on the actual monitored interface rather than assuming the
interface name or disabling checksum validation to hide a warning.

Manage standalone Zeek through the installed systemd unit and ZeekControl. Do not
start a second unmanaged `zeek -i` or `zeekctl deploy` alongside that unit.
`zeek.service` is oneshot with `RemainAfterExit`: `active (exited)` does not prove
the capture process is still alive. Check `zeekctl status`, the real PID and interface.

Evidence: `sensor_agent/setup_vm.sh` and its generated capture helper/unit;
`sensor_agent/README.md`. A known-good setup still needs a bounded traffic probe
and a corresponding new connection record for live capture verification.
