# IoT Device Emulator

Lightweight laboratory to simulate IT/IoT/OT endpoints with persona-specific network behaviour, DHCP fingerprints, and vulnerability toggles. The toolkit ships a **client** image (persona orchestrator) and a **server** image hosting protocol endpoints, logging, and a status API.

## Quick Start
- **Prerequisites**: Linux host recommended, Docker Engine 20+, ability to grant containers `--cap-add=NET_ADMIN`, and multicast-friendly networking (bridge or macvlan). macOS users should avoid macvlan restrictions or run inside a Linux VM.
- **Build images**
  ```bash
  cd server
  docker build -t iot-server .
  cd ../client
  docker build -t iot-client .
  cd ..
  ```
- **Launch the server**
  ```bash
  docker network create --subnet 192.168.50.0/24 server_net || true
  docker run --name iot-server --network server_net --ip 192.168.50.10 \
    -e MODBUS_PORT=1502 \
    -v $(pwd)/data:/data -d iot-server
  ```
- **Start a client persona**
  ```bash
  docker run --rm --cap-add=NET_ADMIN \
    --network server_net \
    -e DEVICE_TYPE=CAMERA_RTSP \
    -e DEVICE_ID=cam01 \
    -e SERVER_IP=192.168.50.10 \
    -e MODBUS_PORT=1502 \
    iot-client
  ```
- **Verify DHCP & mapping**
  ```bash
  tests/verify_dhcp.sh iot-client 192.168.50.10
  python scripts/mapper/mapper_service.py --server-ip 192.168.50.10
  curl http://192.168.50.10:8080/status
  ```

## Personas
Persona definitions live in `client/profiles.yaml` and `configs/persona_matrix.csv`. Each persona captures DHCP identifiers, firmware strings, protocols, payload templates, discovery chatter, and vulnerability profile flags.

| Key | Summary | Protocol Highlights |
|-----|---------|---------------------|
| CAMERA_RTSP | Industrial camera streaming RTSP and ONVIF discovery | RTSP, HTTP, ONVIF |
| PRINTER_SERVICE | Network printer with IPP/LPD queueing and SNMP status | IPP, LPD, SNMP |
| IP_PHONE_SIP | SIP handset with REGISTER/RTP keepalive | SIP, RTP |
| SMART_TV | Smart display issuing SSDP/mDNS and TLS API calls | SSDP, HTTP, TLS |
| SMART_SPEAKER | Voice assistant broadcasting mDNS and MQTT telemetry | MQTT, HTTP |
| THERMOSTAT_MQTT | HVAC controller posting climate metrics | MQTT |
| SMART_PLUG_COAP | Connected plug toggling loads over CoAP | CoAP, HTTP |
| NVR_SIM | Recorder pulling RTSP and pushing SMB-like metadata | RTSP, SMB, HTTP |
| PROJECTOR_SNMP | Projector emitting SNMP traps and checking configs | SNMP, HTTP |
| SMART_WATCH | Wearable sending periodic HTTPS metrics | HTTPS |
| PLC_MODBUS | PLC polling/writing Modbus registers | Modbus/TCP, HTTP |
| SCADA_SENSOR | Sensor gateway blending MQTT telemetry and Modbus reads | MQTT, Modbus |
| HMI_PANEL | Operator panel querying HTTP APIs plus Modbus interactions | HTTP, Modbus |
| BACNET_DEVICE | BACnet/IP controller broadcasting who-is / i-am | BACnet/IP |
| PROFINET_LIGHT | Profinet beacon advertising presence | Profinet |
| LIGHTING_CONTROLLER | Lighting hub orchestrating MQTT and CoAP commands | MQTT, CoAP |
| XRAY_DICOM | X-ray modality pushing metadata-only DICOM | DICOM |
| ECG_MQTT | ECG monitor streaming waveform telemetry | MQTT |
| INFUSION_PUMP | Infusion pump emitting SNMP traps and secure updates | SNMP, MQTT, HTTPS |
| MRI_DICOM | MRI modality transferring sequences via DICOM | DICOM |

Additional persona details and port lists are documented in `client/README.device-list.md`.

## MAC Handling & SAFE_MODE
`client/common/macgen.sh` generates MAC addresses by concatenating the persona vendor OUI with random suffix bytes, storing allocations in `/var/lib/iot-macs/assigned_macs.txt` to avoid duplication. The client entrypoint applies the MAC with `ip link set eth0 address <MAC>` before DHCP negotiation.

- Grant `--cap-add=NET_ADMIN` for realistic MAC churn.
- Set `SAFE_MODE=true` to skip the in-container MAC change; orchestrators can then provide `--mac-address` externally while still benefiting from persona-specific DHCP identifiers.

## Persona Enhancements
- **Firmware propagation**: `FIRMWARE_VERSION` is embedded into DHCP vendor-class/client-id strings, HTTP headers, MQTT client IDs, and DICOM metadata.
- **Discovery chatter**: `client/common/chatter_generator.sh` emits periodic mDNS, SSDP, and ARP probes. Tune with `DISCOVERY_INTENSITY=low|med|high` or disable with `ENABLE_BROADCAST=false`.
- **Pairing chatter**: Personas with `pairing_chatter` lists will log simulated onboarding events and can be extended to call REST pairing hooks.
- **Vulnerability toggles**: `client/common/vuln_injector.py` introduces weak TLS ciphers, default credentials, or attack-mode beacons based on the persona `vulnerability_profile`. Enable globally with `MALICIOUS_MODE=true`.
- **Payload realism**: `client/common/payload_generator.py` renders JSON payload templates with jitter, waveform synthesis, and register ranges per persona.

## Orchestration at Scale
- **Spawner**: `python scripts/spawner.py --server-ip 192.168.50.10 --count 10` rapidly launches persona mixtures. Use `--dry-run` to review docker commands.
- **docker-compose**: See `docker-compose.yml.example` for a baseline topology. Comments outline macvlan usage where supported.
- **Mapper service**: Run `scripts/mapper/mapper_service.py` (optionally in a container) to populate `/data/mappings.json` with `{MAC → DEVICE_TYPE, DEVICE_ID, FIRMWARE_VERSION, IP}`. The server status API exposes the same mapping at `/status/mappings`.

## DNS & Hosts Mapping
Provide `HOSTNAME_MAP` (comma-separated `name` or `name=ip` entries) to the client to extend `/etc/hosts`. By default, entries resolve to `SERVER_IP`. The template driving `/etc/dhcp/dhclient.conf` lives in `configs/dhclient.jinja` should further customization be required.

## Logs & Observability
- **Logshipper**: Clients POST JSON events to `http://SERVER_IP:9300/ingest`. Raw events accumulate under `/data/logs/events.log`.
- **Status API**: `http://SERVER_IP:8080/status` summarises recent activity and exposes the mapping table. `/status/logs` returns the full log tail for ad-hoc troubleshooting.
- **PAN-OS validation**: Refer to `docs/panos_validation.md` and `tests/pan_capture_integration.md` when validating Device-ID classification.

## Tests & CI
- Shell helpers live in `tests/*.sh` for DHCP, MAC, and protocol smoke tests.
- Python unit tests under `tests/test_*.py` cover payload templating and mapping logic.
- GitHub Actions (`.github/workflows/ci.yml`) runs `shellcheck`, `flake8`, and `pytest` on every push/PR.

## Contribution Guidelines
- Prefer reusable utilities under `client/common` when adding new personas.
- Keep persona metadata synchronized between `client/profiles.yaml`, `configs/persona_matrix.csv`, and `client/common/payload_templates/`.
- Maintain JSON logging for new scripts to preserve mapper compatibility.
- Run `flake8` and `pytest` locally before submitting PRs; ensure shell scripts stay `shellcheck` clean.

## License & Contact
- Licensed under the [MIT License](LICENSE) (to be added).
- For questions or contributions, open an issue in this repository or contact the lab maintainers.
