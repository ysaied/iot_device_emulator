#!/usr/bin/env python3
from __future__ import annotations

import json
import time

import paho.mqtt.client as mqtt

from .common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def main() -> None:
    client = mqtt.Client(client_id=f"{DEVICE_ID}-thermo")
    client.connect(SERVER_IP, 1883, keepalive=60)
    client.loop_start()
    try:
        while True:
            telemetry = {
                "device_id": DEVICE_ID,
                "firmware": FIRMWARE_VERSION,
                "temperature_c": round(21.0 + jitter(1.0) - 1.0, 2),
                "humidity_pct": round(40.0 + jitter(0.5) - 0.5, 2),
            }
            client.publish(f"thermostat/{DEVICE_ID}/telemetry", json.dumps(telemetry), qos=0)
            json_log("mqtt_publish", topic=f"thermostat/{DEVICE_ID}/telemetry")
            malicious_ping("/thermostat")
            time.sleep(jitter(30))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
