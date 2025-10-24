# Device-Hub IoT Emulator

The lab now models **device containers** that run persona-specific scripts and a central **hub container** that orchestrates registration and outbound probes. Each persona defines whether it acts as a `client`, `server`, or `both` role at runtime.

## Architecture Overview

- **Hub container**
  - Runs `registry_service.py` (FastAPI + SQLite) on port `7000/tcp` for device registration.
  - Runs `connection_manager.py`, which polls the registry and initiates probes towards device containers based on registered protocols:
    - Modbus TCP → `1502/tcp`
    - DICOM C-STORE/SCP → `11112/tcp`
    - RTSP → `8554/tcp`
    - IPP → `6310/tcp`
    - SNMP → `16100/udp`
  - Maintains state: `device_id`, `device_type`, `role`, `ip_address`, `protocols`, `last_seen_timestamp`, `firmware`, `mac`.

- **Device containers** (single unified image under `devices/`)
  - Obtain IP via DHCP, adjust MAC from persona, parse persona role + protocols from `configs/persona_matrix.csv`.
  - Register with the hub using `HUB_IP` via HTTP POST `/register` (JSON payload includes role, protocols, firmware, MAC).
  - Behave according to role:
    - `client`: initiate outbound flows (e.g., PLC Modbus polling, SIP REGISTER, MQTT publishing) towards hub or peer services.
    - `server`: start listeners (e.g., Modbus TCP server on `1502/tcp`, DICOM SCP on `11112/tcp`, RTSP server on `8554/tcp`, IPP server on `6310/tcp`, SNMP agent on `16100/udp`).
    - `both`: run both client routines and server listeners concurrently.
  - Common utilities in `devices/scripts/common.py` expose `is_client()` / `is_server()` toggles for personas.

## Active Protocols & Ports

| Persona Role | Outbound Client Protocols | Server Listeners (Device) | Hub Services |
|--------------|---------------------------|---------------------------|--------------|
| `client`     | MQTT (`1883/tcp`), HTTP/HTTPS (`80/443/tcp`), SIP (`5060/udp`), RTSP (`8554/tcp`), CoAP (`5683/udp`), BACnet (`47808/udp`), Profinet (`34964/udp`), Modbus TCP (`1502/tcp` as client), DICOM (`11112/tcp` towards hub), SNMP (`16100/udp` towards hub) | none | Registry API (`7000/tcp`), connection probes (above protocols to registered IPs) |
| `server`     | optional ONVIF/mDNS chatter | RTSP server (`8554/tcp`), DICOM SCP (`11112/tcp`), HTTP metadata (`80/443/tcp`) | Registry service + probes |
| `both`       | Modbus client polling (`1502/tcp`) | Modbus TCP server (`1502/tcp`) | Registry service + probes |

> Hub probes run periodically to validate reachability; failed probes log `hub_probe_failed` events.

### Persona Protocol Matrix

| Device Type | Role | Client Connections (→ Hub) | Server Listeners (← Device) |
|-------------|------|----------------------------|-----------------------------|
| CAMERA_RTSP | server | — | RTSP `8554/tcp` |
| PRINTER_SERVICE | server | — | IPP `6310/tcp`, SNMP `16100/udp` |
| IP_PHONE_SIP | client | SIP `5060/udp`, RTP keepalive `16384/udp` | — |
| SMART_TV | client | HTTP `8008/tcp`, HTTPS `443/tcp`, SSDP `1900/udp` | — |
| SMART_SPEAKER | client | MQTT `1883/tcp` | — |
| THERMOSTAT_MQTT | client | MQTT `1883/tcp` | — |
| SMART_PLUG_COAP | client | CoAP `5683/udp`, HTTP `80/tcp` | — |
| NVR_SIM | client | RTSP `554/tcp`, HTTP `80/tcp` | — |
| PROJECTOR_SNMP | client | SNMP `161/udp`, HTTP `80/tcp` | — |
| SMART_WATCH | client | HTTPS `443/tcp`, MQTT `8883/tcp` | — |
| PLC_MODBUS | both | Modbus TCP `1502/tcp` | Modbus TCP `1502/tcp` |
| SCADA_SENSOR | client | MQTT `1883/tcp`, Modbus TCP `1502/tcp` | — |
| HMI_PANEL | client | HTTP `80/tcp`, Modbus TCP `1502/tcp` | — |
| BACNET_DEVICE | client | BACnet/IP `47808/udp` | — |
| PROFINET_LIGHT | client | Profinet discovery `34964/udp` | — |
| LIGHTING_CONTROLLER | client | MQTT `1883/tcp`, CoAP `5683/udp` | — |
| XRAY_DICOM | server | — | DICOM `11112/tcp` |
| ECG_MQTT | client | MQTT `1883/tcp`, HTTPS `443/tcp` | — |
| INFUSION_PUMP | client | MQTT `1883/tcp`, SNMP traps `162/udp`, HTTPS `443/tcp` | — |
| MRI_DICOM | client | DICOM `11112/tcp`, HTTPS `443/tcp` | — |

## Workflow

1. **Build images**
   ```bash
   cd hub
   docker build -t iot-hub .
   cd ../devices
   docker build -t iot-device .
   cd ..
   ```
2. **Compose deployment** (extract from `docker-compose.yml.example`):
   - Hub service with static IP (e.g., `192.168.50.10`).
   - Multiple device services using the unified `iot-device` image, each with `DEVICE_TYPE`, `DEVICE_ID`, `ROLE`, `HUB_IP`.
3. **Run**
   ```bash
   docker compose up hub device-camera device-printer device-plc
   ```
   Devices register with hub, start appropriate listeners/clients, and their logs surface `hub_registered` events.

## Adding Personas

- Update `configs/persona_matrix.csv` with role + protocols.
- Extend `devices/profiles.yaml` to include role, listener config.
- Implement/extend script in `devices/scripts/` to respect `is_client()` / `is_server()` and start/stop appropriate services.
- When new server protocols are introduced, ensure `hub/connection_manager.py` knows the probe port.

## Hub Logging

- Registration events: `{

## Hub Logging & Observability

- Hub registry endpoint: `GET http://<HUB_IP>:7000/devices`
- Registration events: `{"event":"hub_registered","device_id":"plc01","hub":"192.168.50.10"}`
- Probe events: `hub_probe_success` / `hub_probe_failed` with protocol and port metadata
- Device listener logs: `modbus_server_start`, `dicom_store`, `ipp_server_request`, etc.

## Contribution Guidelines

- Prefer reusable utilities under `devices/common` when adding new personas.
- Keep persona metadata synchronized between `devices/profiles.yaml`, `configs/persona_matrix.csv`, and `devices/common/payload_templates/`.
- Maintain JSON logging format for compatibility with the hub registry and connection manager.
- Run `flake8` and `pytest` locally before submitting PRs; ensure shell scripts stay `shellcheck` clean.

## License & Contact

- Licensed under the [MIT License](LICENSE) (to be added).
- For questions or contributions, open an issue in this repository or contact the lab maintainers.
