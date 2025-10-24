#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import time

import paho.mqtt.client as mqtt

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def send_coap_command(group: str, state: str) -> None:
    payload = json.dumps({"group": group, "state": state, "firmware": FIRMWARE_VERSION}).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(payload, (SERVER_IP, 5683))
    sock.close()
    json_log("coap_command", group=group, state=state)


def main() -> None:
    client = mqtt.Client(client_id=f"{DEVICE_ID}-lighting")
    client.connect(SERVER_IP, 1883, keepalive=60)
    client.loop_start()
    try:
        index = 0
        groups = ["zone1", "zone2"]
        states = ["on", "off"]
        while True:
            group = groups[index % len(groups)]
            state = states[index % len(states)]
            message = {"group": group, "state": state, "firmware": FIRMWARE_VERSION}
            client.publish(f"lighting/{group}/command", json.dumps(message))
            json_log("mqtt_publish", topic=f"lighting/{group}/command", state=state)
            send_coap_command(group, state)
            malicious_ping("/lighting")
            index += 1
            time.sleep(jitter(20))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
