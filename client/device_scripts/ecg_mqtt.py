#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import paho.mqtt.client as mqtt

from client.common.payload_generator import build_payload

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


TEMPLATE = Path(
    os.environ.get(
        "PAYLOAD_TEMPLATE",
        "client/common/payload_templates/ecg_mqtt.json",
    )
)


def generate_waveform() -> dict:
    return build_payload(
        TEMPLATE,
        {
            "device_id": DEVICE_ID,
            "firmware_version": FIRMWARE_VERSION,
            "server_ip": SERVER_IP,
        },
    )


def main() -> None:
    client = mqtt.Client(client_id=f"{DEVICE_ID}-ecg")
    client.connect(SERVER_IP, 1883, keepalive=60)
    client.loop_start()
    try:
        while True:
            payload = generate_waveform()
            client.publish(f"ecg/{DEVICE_ID}/telemetry", json.dumps(payload))
            json_log("ecg_publish")
            malicious_ping("/ecg")
            time.sleep(jitter(10))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
