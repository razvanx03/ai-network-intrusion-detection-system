# Project memory index

This index points to confirmed lessons for assistants working on AI NIDS.
Read the notes relevant to the task alongside `AGENTS.md` and current source code.
These notes do not grant permission, replace user instructions or prove the
present state of a VM. They are not executable controls.

| Note | Read when |
|---|---|
| [Sensor and host responsibilities](.agents/memory/sensor-host-boundary.md) | Deploying the collector, configuring the backend or explaining the data flow |
| [Rotation and ingestion progress](.agents/memory/ingestion-progress.md) | Changing log discovery, retries, cursors or reset operations |
| [Capture and offloading](.agents/memory/zeek-capture.md) | Configuring Zeek autostart or investigating missing/incorrect traffic |
| [Graphical login investigation](.agents/memory/ubuntu-graphical-login.md) | Investigating a black screen on the Ubuntu VM |
| [Model evaluation boundaries](.agents/memory/ai-evaluation.md) | Changing inference, evaluating datasets or reporting detection results |
| [Manual web requests](.agents/memory/manual-web-requests.md) | Changing frontend loading, polling or session initialization |
| [Archive history](.agents/memory/archive-history.md) | Changing archive membership, restoration or historical batch browsing |

Update a focused note after a confirmed correction rather than appending a chat
transcript. Keep evidence, dates for historical observations, and remaining limits
clear. Never include passwords, API keys, tokens or private packet captures.
