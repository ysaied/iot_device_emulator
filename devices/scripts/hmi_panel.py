#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time

import requests
from pymodbus.client import ModbusTcpClient

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "1502"))


def http_query() -> None:
    try:
        resp = requests.get(f"http://{SERVER_IP}/hmi/overview", timeout=5)
        json_log("http_query", status=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("http_error", error=str(exc))


def modbus_cycle(client: ModbusTcpClient) -> None:
    rr = client.read_holding_registers(10, 2, unit=3)
    json_log("modbus_read", registers=rr.registers if rr else [])
    client.write_register(12, int(jitter(100)))
    json_log("modbus_write", register=12)


def main() -> None:
    client = ModbusTcpClient(SERVER_IP, port=MODBUS_PORT)
    client.connect()
    try:
        while True:
            http_query()
            modbus_cycle(client)
            malicious_ping("/hmi")
            time.sleep(jitter(30))
    finally:
        client.close()


if __name__ == "__main__":
    main()
