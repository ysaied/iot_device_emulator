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

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, json_log, jitter, malicious_ping


def send_beacon(state: str) -> None:
    payload = json.dumps(
        {
            "device_id": DEVICE_ID,
            "firmware": FIRMWARE_VERSION,
            "state": state,
        }
    ).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(payload, ("255.255.255.255", 34964))
    sock.close()
    json_log("profinet_beacon", state=state)


def main() -> None:
    state = "ready"
    while True:
        send_beacon(state)
        malicious_ping("/profinet")
        state = "standby" if state == "ready" else "ready"
        time.sleep(jitter(25))


if __name__ == "__main__":
    main()
