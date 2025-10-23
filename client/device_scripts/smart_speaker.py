#!/usr/bin/env python3
from __future__ import annotations

import os
import time

import paho.mqtt.client as mqtt

from client.common.vulnerability_toggles import get_profile
from client.common.vuln_injector import mutate_mqtt_client_id

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


PROFILE = get_profile(os.environ.get("VULNERABILITY_PROFILE", "none"))
TOPIC_BASE = f"speaker/{DEVICE_ID}"


def on_message(_client, _userdata, msg):  # noqa: ANN001
    json_log("mqtt_message", topic=msg.topic, payload=msg.payload.decode(errors="ignore"))


def build_client() -> mqtt.Client:
    client_id = mutate_mqtt_client_id(f"{DEVICE_ID}-speaker", PROFILE, FIRMWARE_VERSION)
    client = mqtt.Client(client_id=client_id, clean_session=True)
    if PROFILE.weak_tls:
        client.tls_set()
        client.tls_insecure_set(True)
    client.on_message = on_message
    return client


def main() -> None:
    client = build_client()
    client.connect(SERVER_IP, 1883, keepalive=60)
    client.loop_start()
    client.subscribe(f"{TOPIC_BASE}/command")
    try:
        while True:
            payload = {
                "device_id": DEVICE_ID,
                "firmware": FIRMWARE_VERSION,
                "volume": 35,
            }
            client.publish(f"{TOPIC_BASE}/telemetry", payload=str(payload), qos=0)
            json_log("mqtt_publish", topic=f"{TOPIC_BASE}/telemetry")
            malicious_ping("/speaker")
            time.sleep(jitter(20))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
