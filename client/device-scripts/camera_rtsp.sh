#!/usr/bin/env bash
set -euo pipefail

SERVER_IP="${SERVER_IP:-127.0.0.1}"
DEVICE_ID="${DEVICE_ID:-camera-demo}"
FIRMWARE_VERSION="${FIRMWARE_VERSION:-0.0.0}"
FFMPEG_STREAM="${FFMPEG_STREAM:-false}"

log() {
  python3 - <<'PY' "${DEVICE_ID}" "${FIRMWARE_VERSION}" "${1}" "${2}"
import json
import sys
device_id, fw, event, detail = sys.argv[1:5]
print(json.dumps({"event": event, "detail": detail, "device_id": device_id, "firmware_version": fw}))
PY
}

send_rtsp_options() {
  python3 - <<'PY' "${SERVER_IP}" "${DEVICE_ID}" "${FIRMWARE_VERSION}"
import socket
import sys

server_ip, device_id, firmware = sys.argv[1:4]
message = (
    "OPTIONS rtsp://{0}:554/stream/{1} RTSP/1.0\\r\\n"
    "CSeq: 1\\r\\n"
    "User-Agent: Camera/{2}\\r\\n\\r\\n"
).format(server_ip, device_id, firmware)
try:
    sock = socket.create_connection((server_ip, 554), timeout=5)
    sock.sendall(message.encode())
    sock.close()
except Exception as exc:  # noqa: BLE001
    print(json.dumps({"event": "rtsp_error", "error": str(exc), "device_id": device_id}), flush=True)
PY
}

if [[ "${FFMPEG_STREAM}" == "true" ]]; then
  log "rtsp_stream" "starting-ffmpeg"
  ffmpeg -re -f lavfi -i testsrc=size=640x480:rate=15 -vcodec libx264 -f rtsp "rtsp://${SERVER_IP}:8554/${DEVICE_ID}" || true &
  STREAM_PID=$!
else
  STREAM_PID=""
fi

trap '[[ -n "${STREAM_PID}" ]] && kill "${STREAM_PID}" 2>/dev/null || true' EXIT

while true; do
  send_rtsp_options
  log "rtsp_keepalive" "sent-options"
  sleep 15
done
