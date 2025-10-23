#!/usr/bin/env bash
set -euo pipefail

SERVER_IMAGE="${1:-iot-server}"
CLIENT_IMAGE="${2:-iot-client}"
NETWORK="${3:-iot-lab}"

docker network create "${NETWORK}" >/dev/null 2>&1 || true

docker rm -f iot-server-test >/dev/null 2>&1 || true
docker run --name iot-server-test \
  --network "${NETWORK}" \
  --ip 192.168.50.10 \
  -d "${SERVER_IMAGE}" >/dev/null

launch_client() {
  local type="$1"
  local id="$2"
  timeout 45 docker run --rm \
    --network "${NETWORK}" \
    --cap-add=NET_ADMIN \
    -e DEVICE_TYPE="${type}" \
    -e DEVICE_ID="${id}" \
    -e SERVER_IP=192.168.50.10 \
    "${CLIENT_IMAGE}" &
}

launch_client CAMERA_RTSP cam01
launch_client PRINTER_SERVICE prn01
launch_client PLC_MODBUS plc01

sleep 40
wait || true

docker logs iot-server-test > /tmp/server.log

docker rm -f iot-server-test >/dev/null 2>&1 || true

grep -q "mqtt" /tmp/server.log && echo "MQTT traffic detected"
grep -q "modbus" /tmp/server.log && echo "Modbus traffic detected"
grep -q "rtsp" /tmp/server.log && echo "RTSP traffic detected"
