#!/usr/bin/env bash
set -euo pipefail

DISCOVERY_INTENSITY="${DISCOVERY_INTENSITY:-low}"
DEVICE_TYPE="${DEVICE_TYPE:-UNKNOWN}"
DEVICE_ID="${DEVICE_ID:-demo}"
SERVER_IP="${SERVER_IP:-127.0.0.1}"

interval() {
  case "${DISCOVERY_INTENSITY}" in
    high) echo 5 ;;
    med) echo 15 ;;
    *) echo 30 ;;
  esac
}

send_mdns() {
  python3 - <<'PY' "${DEVICE_ID}" "${DEVICE_TYPE}"
import socket
import sys

device_id, device_type = sys.argv[1:3]
message = f'_iot._udp.local name={device_id} type={device_type}'
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
sock.sendto(message.encode(), ("224.0.0.251", 5353))
sock.close()
PY
}

send_ssdp() {
  python3 - <<'PY' "${DEVICE_ID}" "${DEVICE_TYPE}" "${SERVER_IP}"
import socket
import sys

device_id, device_type, server_ip = sys.argv[1:4]
message = (
    "NOTIFY * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    f"NT: urn:schemas-upnp-org:device:{device_type}:1\r\n"
    f"USN: uuid:{device_id}\r\n"
    f"LOCATION: http://{server_ip}/device/{device_id}\r\n"
    "NTS: ssdp:alive\r\n"
    "CACHE-CONTROL: max-age=1800\r\n\r\n"
)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
sock.sendto(message.encode(), ("239.255.255.250", 1900))
sock.close()
PY
}

send_arp_probe() {
  logger --tag "chatter_generator" "ARP probe simulated for ${DEVICE_ID}"
}

main_loop() {
  while true; do
    send_mdns || true
    send_ssdp || true
    send_arp_probe || true
    sleep "$(interval)"
  done
}

main_loop
