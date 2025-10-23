# Networking Notes

- **DHCP**: Client containers default to running `dhclient -1 eth0` after applying a persona MAC. Ensure the Docker network or external switch offers a DHCP responder or disable DHCP (`ENABLE_DHCLIENT=false`) and provide static addressing/count.
- **MAC adjustments**: The client entrypoint performs `ip link set eth0 address <MAC>`, requiring `--cap-add=NET_ADMIN` or privileged mode. For environments where elevated capability is not possible, set `SAFE_MODE=true` and supply `--mac-address` via the orchestrator.
- **Service discovery chatter**: mDNS/SSDP packets use multicast (`224.0.0.251:5353`, `239.255.255.250:1900`). If running on macvlan or bridged networks, confirm multicast propagation or disable broadcast chatter with `ENABLE_BROADCAST=false`.
- **Ports**:
  - Server binds TCP `80/443/502/554/8554/8080/9300` and UDP `161/162/5060/5683/47808`. Adjust firewall rules accordingly.
  - Client personas initiate outbound connections to these ports and may emit UDP broadcasts on `47808`, `34964`, and multicast addresses.
- **TLS**: Nginx terminates HTTPS with a self-signed certificate generated during the server build. Clients default to `verify=False`, but you can supply trusted certificates if operating in production labs.
- **Data volume**: Both server and mapper expect a shared `/data` volume. Mount the same host directory into the server container (and mapper script) to persist logs and mapping metadata.
