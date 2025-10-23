#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <client-image> [server-ip]" >&2
  exit 1
fi

CLIENT_IMAGE="$1"
SERVER_IP="${2:-192.168.50.10}"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "Starting DHCP verification using ${CLIENT_IMAGE}"

docker run --rm --cap-add=NET_ADMIN \
  -e DEVICE_TYPE=CAMERA_RTSP \
  -e DEVICE_ID=dhcp-test \
  -e SERVER_IP="${SERVER_IP}" \
  "${CLIENT_IMAGE}" --dry-run > "${TMP_DIR}/dry_run.json"

if ! grep -q "vendor_class" "${TMP_DIR}/dry_run.json"; then
  echo "Expected vendor_class in dry-run output" >&2
  exit 1
fi

docker rm -f iot-dhcp-test >/dev/null 2>&1 || true

docker run --name iot-dhcp-test --cap-add=NET_ADMIN \
  -e DEVICE_TYPE=CAMERA_RTSP \
  -e DEVICE_ID=dhcp-test \
  -e SERVER_IP="${SERVER_IP}" \
  -d "${CLIENT_IMAGE}" >/dev/null

sleep 20
docker logs iot-dhcp-test > "${TMP_DIR}/client.log"
docker rm -f iot-dhcp-test >/dev/null 2>&1 || true

if ! grep -q "dhcp_conf_rendered" "${TMP_DIR}/client.log"; then
  echo "DHCP config was not rendered" >&2
  exit 1
fi

echo "DHCP verification complete"
