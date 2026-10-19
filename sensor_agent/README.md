# Zeek sensor agent

The backend pulls logs on demand. GET /logs returns a bounded batch; the backend validates and commits connections plus alerts, then POST /logs/ack confirms it. Deploy the updated backend and sensor together: the old list-only response is incompatible.

## Installation

On Ubuntu 22.04/24.04 run `bash install_zeek.sh enp0s8`, replacing the interface with the one that sees monitored traffic (`ip link`). The default-route interface may not see other VMs. Configure traffic mirroring or the appropriate virtual-network topology. The installer requires a standalone Zeek configuration. On other distributions install Zeek manually and enable `@load policy/tuning/json-logs` in local.zeek.

Run the collector as an unprivileged service account. Grant read/traverse access to the Zeek log root and newly rotated archives. Create `/var/lib/nids-sensor` owned by that account, mode 0700. Do not run the collector as root.

Copy `.env.example` to `.env`. Fill every setting; paths must be absolute. Generate API_KEY using `python3 -c "import secrets; print(secrets.token_hex(32))"` and set the same secret as SENSOR_AGENT_API_KEY in the backend. Protect .env with mode 0600. ZEEK_LOG_DIR includes both current/ and dated archives. STATE_FILE must be on persistent local storage outside the log tree.

Start with `.venv/bin/python collector.py`. Alternatively use `.venv/bin/uvicorn collector:create_app --factory --host 0.0.0.0 --port 8000` (explicit host/port override is required with uvicorn).

For startup after reboot configure a systemd service with an unprivileged User, absolute WorkingDirectory and ExecStart, Restart=on-failure and UMask=0077. Configure ZeekControl startup/maintenance too: the installer only deploys Zeek for the current boot. Check both after reboot.

Backend settings: SENSOR_MOCK_MODE=False, SENSOR_AGENT_URL=http://VM_PRIVATE_IP:8000, SENSOR_AGENT_API_KEY set to the generated secret. Allow port 8000 only from the backend. Use a trusted private network or HTTPS termination because the API key travels in an HTTP header.

## Protocol and recovery

- All endpoints require X-API-Key, including GET /health.
- GET /logs returns an object with batch_id and records. Each request delivers at most BATCH_SIZE records (1..1000), also bounded by a byte budget. Repeat the action to drain a backlog.
- The pending payload and proposed cursors are saved atomically in SQLite before responding. Retries and restarts return exactly the same pending batch, including an empty batch.
- POST /logs/ack accepts an object with batch_id. Only acknowledgement advances cursors. Repeating the last acknowledgement is safe; unknown identifiers return 409.
- The backend commits connections and alerts together and analyzes only new connection UIDs. If acknowledgement fails, the operation reports failure even though data may already be saved. Retry safely.
- JSON and standard tab-separated conn.log are supported. Incomplete final lines remain unread. Malformed data, unreadable files and corrupted state cause explicit errors.
- Retained conn*.log and conn*.log.gz archives are discovered. A digest of the first complete data record identifies a stream across rename/compression; positions refer to uncompressed bytes. Normal Zeek rotation works regardless of the new file size.
- Retain archives longer than the maximum interval between successful pulls. Deleted unread logs cannot be recovered. Do not edit historical files or use copy-truncate rotation. Concurrent rotation may temporarily fail a request; retry after rotation finishes. Large compressed archives require decompression to seek, so pulls can become slower with a long retention period.
- One sensor state belongs to one consuming backend. SQLite serializes sensor requests. Concurrent backend requests may require retry after a database conflict.
- DELETE /logs resets cursors for all retained files; it never deletes log files and refuses while a batch awaits acknowledgement. Existing backend UIDs remain deduplicated. Clearing the backend database alone does not reset sensor cursors.
- The previous /tmp offset is not migrated. The first run reads retained logs from the start; existing backend UIDs prevent duplicate connections and alerts.

Verify capture, a manual pull, retry, restart with a pending batch, rotation and reboot on the VM. Health confirms the agent/state store is reachable; it does not prove Zeek is capturing traffic.
