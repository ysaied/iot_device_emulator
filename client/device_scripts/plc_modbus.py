#!/usr/bin/env python3
from __future__ import annotations

import os
import random
import time

from pymodbus.client import ModbusTcpClient

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "1502"))


def main() -> None:
    client = ModbusTcpClient(SERVER_IP, port=MODBUS_PORT)
    if not client.connect():
        json_log("modbus_error", error="connect_failed")
        return
    try:
        while True:
            rr = client.read_holding_registers(0, 10, unit=1)
            json_log("modbus_read", registers=rr.registers if rr.isError() is False else "error")
            value = random.randint(0, 4095)
            client.write_register(5, value, unit=1)
            json_log("modbus_write", register=5, value=value)
            malicious_ping("/plc")
            time.sleep(jitter(20))
    finally:
        client.close()


if __name__ == "__main__":
    main()
