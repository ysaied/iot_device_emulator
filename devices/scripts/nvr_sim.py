#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from devices.common.payload_generator import build_payload

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


TEMPLATE = Path(
    os.environ.get(
        "PAYLOAD_TEMPLATE",
        "devices/common/payload_templates/nvr_sim.json",
    )
)


def fetch_rtsp_snapshot() -> None:
    try:
        with socket.create_connection((SERVER_IP, 554), timeout=5) as sock:
            sock.sendall(b"DESCRIBE rtsp://server/stream RTSP/1.0\r\nCSeq: 1\r\n\r\n")
            json_log("rtsp_describe")
    except Exception as exc:  # noqa: BLE001
        json_log("rtsp_error", error=str(exc))


def post_metadata() -> None:
    payload = build_payload(
        TEMPLATE,
        {
            "device_id": DEVICE_ID,
            "firmware_version": FIRMWARE_VERSION,
            "server_ip": SERVER_IP,
        },
    )
    body = json.dumps(payload).encode()
    try:
        with socket.create_connection((SERVER_IP, 80), timeout=5) as sock:
            request = (
                "POST /nvr/metadata HTTP/1.1\r\n"
                f"Host: {SERVER_IP}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n\r\n"
            ).encode() + body
            sock.sendall(request)
            json_log("metadata_post", size=len(body))
    except Exception as exc:  # noqa: BLE001
        json_log("metadata_error", error=str(exc))


def main() -> None:
    while True:
        fetch_rtsp_snapshot()
        post_metadata()
        malicious_ping("/nvr")
        time.sleep(jitter(40))


if __name__ == "__main__":
    main()
