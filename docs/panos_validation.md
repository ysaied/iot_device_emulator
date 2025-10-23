# PAN-OS Validation Playbook

## Objectives
- Confirm that PAN-OS Device-ID classifies emulated personas by MAC address and observed telemetry.
- Validate policy enforcement and log correlation using the generated `/data/mappings.json` table.

## Prerequisites
- IoT Emulator server container reachable from monitored segments.
- PAN-OS device with Device-ID / IoT Security licensing enabled.
- SPAN/TAP or routed path so PAN-OS observes client↔server traffic.

## Workflow
1. **Start server services**
   ```bash
   docker run -d --name iot-server \
     --network server_net \
     --ip 192.168.50.10 \
     -v $(pwd)/data:/data \
     iot-server
   ```
2. **Launch sample personas**
   ```bash
   docker run --rm --cap-add=NET_ADMIN \
     --network server_net \
     -e DEVICE_TYPE=CAMERA_RTSP \
     -e DEVICE_ID=cam01 \
     -e SERVER_IP=192.168.50.10 \
     -v $(pwd)/data:/data \
     iot-client
   ```
   Repeat for additional personas (printer, PLC, MQTT sensor).
3. **Collect mapping file**: Run `scripts/mapper/mapper_service.py` until `/data/mappings.json` contains all active MAC entries.
4. **PAN-OS verification**:
   - In the web UI, navigate to *Monitor → Logs → Traffic* and filter on the client IP range.
   - Inspect the *Source* and *Device-ID* columns for the expected persona labels.
   - Export the log subset and compare MAC addresses with `mappings.json`.
5. **Policy checks**:
   - Create a Device-ID policy rule that matches one persona (e.g., `Device = IoT Camera`).
   - Trigger the persona traffic again and confirm the policy hit count increments.
6. **Archive evidence**:
   - Store `/data/logs/events.log`, `/data/mappings.json`, and relevant PAN-OS reports for future regression tracking.
   - Note firmware versions and vulnerability flags used during the test.
