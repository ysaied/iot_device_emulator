# Architecture Overview

The IoT Device Emulator repository provides two container images and supporting tooling:

- **Client image** – Runs persona scripts that emulate IoT/OT device traffic. A shell entrypoint renders persona metadata, adjusts the container MAC address, launches DHCP, and orchestrates protocol chatter. Device scripts use shared helpers (`client/common`) for JSON logging, payload generation, vulnerability toggles, and malicious-mode beacons.
- **Server image** – Aggregates lightweight protocol endpoints (MQTT, Modbus/TCP, RTSP, SIP, SNMP, CoAP, BACnet, DICOM, HTTP/HTTPS) under `supervisord`. Custom Python services supplement packages from the base distribution to keep footprint small while providing deterministic logging via `server/logshipper.py` and visibility through `server/status_api.py`.
- **Mapper service** – Optional host-side helper that consumes server log output and writes `/data/mappings.json`, offering a MAC-to-device manifest for integration with PAN-OS Device-ID or other security analytics.

```text
+-------------------+           +-----------------------+
| client container   |  DHCP /   |       server          |
|  entrypoint.sh     |<--------->|  supervisord + apps   |
|  device scripts    |  App traffic / telemetry / logs  |
+-------------------+           +-----------------------+
         |                                     |
         +---- logshipper HTTP ingest ---------+
         |                                     |
         +---- mapper_service writes mappings--+
```

Key design notes:

- Personas are defined declaratively in `client/profiles.yaml` and mirrored in `configs/persona_matrix.csv`. Each persona references protocol ports, DHCP identifiers, payload templates, and vulnerability profiles.
- Shared utilities encapsulate cross-cutting concerns: `macgen.sh` (vendor OUI-aware MAC allocation), `payload_generator.py` (randomised JSON/binary payloads), `chatter_generator.sh` (mDNS/SSDP/ARP beacons), and `vuln_injector.py` (weak TLS, legacy credentials, attack-mode beacons).
- The server avoids heavyweight daemons when possible by implementing protocol stubs in Python, reducing build complexity while still producing realistic traffic and logs.
- Logging is JSON-first across components. Logshipper writes to `/data/logs/events.log`, which powers the status API and downstream analytics.
