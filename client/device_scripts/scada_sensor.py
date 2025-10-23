#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time

import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "1502"))


def main() -> None:
    mqtt_client = mqtt.Client(client_id=f"{DEVICE_ID}-sensor")
    mqtt_client.connect(SERVER_IP, 1883, keepalive=60)
    mqtt_client.loop_start()
    modbus_client = ModbusTcpClient(SERVER_IP, port=MODBUS_PORT)
    modbus_client.connect()
    try:
        while True:
            registers = modbus_client.read_input_registers(0, 4, unit=2)
            telemetry = {
                "lux": round(400 + jitter(50), 2),
                "vibration": round(0.3 + jitter(0.1) - 0.1, 3),
                "firmware": FIRMWARE_VERSION,
                "registers": registers.registers if registers else [],
            }
            mqtt_client.publish(f"scada/{DEVICE_ID}/telemetry", json.dumps(telemetry))
            json_log("scada_publish")
            malicious_ping("/scada")
            time.sleep(jitter(35))
    finally:
        modbus_client.close()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
