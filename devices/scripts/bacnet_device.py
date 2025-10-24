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

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def send_bacnet(message_type: str) -> None:
    payload = json.dumps(
        {
            "type": message_type,
            "device_id": DEVICE_ID,
            "firmware": FIRMWARE_VERSION,
        }
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, ("255.255.255.255", 47808))
    sock.close()
    json_log("bacnet_message", message=message_type)


def directed_request() -> None:
    payload = json.dumps(
        {
            "type": "read-property",
            "device_id": DEVICE_ID,
            "property": "presentValue",
        }
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(payload, (SERVER_IP, 47808))
    sock.close()
    json_log("bacnet_directed")


def main() -> None:
    while True:
        send_bacnet("who-is")
        send_bacnet("i-am")
        directed_request()
        malicious_ping("/bacnet")
        time.sleep(jitter(30))


if __name__ == "__main__":
    main()
