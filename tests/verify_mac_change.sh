#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <client-image> [device-type]" >&2
  exit 1
fi

CLIENT_IMAGE="$1"
DEVICE_TYPE="${2:-CAMERA_RTSP}"

docker rm -f mac-check >/dev/null 2>&1 || true

docker run --name mac-check --cap-add=NET_ADMIN \
  -e DEVICE_TYPE="${DEVICE_TYPE}" \
  -e DEVICE_ID=mac-test \
  -e SERVER_IP=127.0.0.1 \
  "${CLIENT_IMAGE}" --dry-run > /tmp/mac-dry-run.json

MAC=$(python3 -c 'import json,sys;data=json.load(open(sys.argv[1]));print(data.get("detail","unknown"))' /tmp/mac-dry-run.json)
echo "Dry-run MAC: ${MAC:-unknown}"

docker run --name mac-check --cap-add=NET_ADMIN \
  -e DEVICE_TYPE="${DEVICE_TYPE}" \
  -e DEVICE_ID=mac-test \
  -e SERVER_IP=127.0.0.1 \
  -d "${CLIENT_IMAGE}" >/dev/null

sleep 10
docker exec mac-check ip -o link show eth0 > /tmp/mac-actual.txt
docker rm -f mac-check >/dev/null 2>&1 || true

if ! grep -q "link/ether" /tmp/mac-actual.txt; then
  echo "Unable to detect MAC address" >&2
  exit 1
fi

echo "Observed MAC state:"
cat /tmp/mac-actual.txt
