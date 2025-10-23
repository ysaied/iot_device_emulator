#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import time

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def send_coap(method: str, path: str, payload: bytes | None = None) -> None:
    message = {
        "method": method,
        "path": path,
        "device": DEVICE_ID,
        "firmware": FIRMWARE_VERSION,
    }
    if payload:
        message["payload"] = payload.decode(errors="ignore")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(message).encode(), (SERVER_IP, 5683))
    sock.close()
    json_log("coap_send", method=method, path=path)


def main() -> None:
    state = False
    while True:
        state = not state
        payload = json.dumps({"state": "on" if state else "off", "firmware": FIRMWARE_VERSION}).encode()
        send_coap("PUT", "/device/state", payload)
        malicious_ping("/coap")
        time.sleep(jitter(25))


if __name__ == "__main__":
    main()
