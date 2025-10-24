| Device Type | Description | Primary Protocols |
|-------------|-------------|-------------------|
| CAMERA_RTSP | Industrial IP camera streaming RTSP and ONVIF metadata | RTSP, HTTP, ONVIF |
| PRINTER_SERVICE | Network printer with IPP/LPD queueing and SNMP status | IPP, LPD, SNMP |
| IP_PHONE_SIP | VoIP handset performing SIP registrations and RTP keepalive | SIP, RTP |
| SMART_TV | Smart display announcing via SSDP/mDNS with TLS API calls | SSDP, HTTP, TLS |
| SMART_SPEAKER | Voice assistant leveraging MQTT control channels | MQTT, HTTP |
| THERMOSTAT_MQTT | HVAC thermostat sending climate telemetry | MQTT |
| SMART_PLUG_COAP | Smart plug toggling load via CoAP commands | CoAP, HTTP |
| NVR_SIM | Network video recorder ingesting camera streams and posting metadata | RTSP, SMB, HTTP |
| PROJECTOR_SNMP | Projector emitting SNMP traps and pulling config | SNMP, HTTP |
| SMART_WATCH | Wearable pushing health telemetry over HTTPS | HTTPS |
| PLC_MODBUS | Industrial PLC polling Modbus registers and writing setpoints | Modbus/TCP, HTTP |
| SCADA_SENSOR | Sensor gateway blending MQTT telemetry with Modbus reads | MQTT, Modbus/TCP |
| HMI_PANEL | Operator panel issuing HTTP queries and Modbus interactions | HTTP, Modbus/TCP |
| BACNET_DEVICE | Building controller broadcasting BACnet who-is/I-am | BACnet/IP |
| PROFINET_LIGHT | Lightweight Profinet beacon advertising presence | Profinet |
| LIGHTING_CONTROLLER | Lighting hub orchestrating MQTT and CoAP group control | MQTT, CoAP |
| XRAY_DICOM | X-ray modality pushing metadata-only DICOM studies | DICOM |
| ECG_MQTT | ECG monitor streaming waveform telemetry via MQTT | MQTT |
| INFUSION_PUMP | Infusion pump emitting SNMP traps and secure updates | SNMP, MQTT, HTTPS |
| MRI_DICOM | MRI modality simulating DICOM series transfers | DICOM |
