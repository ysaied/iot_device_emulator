# PAN-OS Capture Integration

1. Deploy the server container on a PAN-OS‑monitored segment (static IP recommended: `192.168.50.10`).
2. Launch a subset of personas with deterministic MAC addresses (set `SAFE_MODE=true` and supply `VENDOR_OUI` when needed).
3. On PAN-OS, create a policy to allow and log all traffic between the client VLAN and the lab network.
4. Enable packet capture on the relevant PAN-OS interfaces for the duration of the test.
5. Run `scripts/mapper/mapper_service.py` and ensure `/data/mappings.json` is populated; archive this file for comparison.
6. Trigger the quick validation scripts:
   - `tests/verify_dhcp.sh iot-client 192.168.50.10`
   - `tests/verify_protocols.sh iot-server iot-client lab_net`
7. In PAN-OS Device-ID / IoT Security dashboard, verify that the MAC addresses emitted by the emulator resolve to the expected device types.
8. Export correlations (CSV or report) and store alongside `mappings.json` for future regression analysis.
