#!/usr/bin/env python3
from __future__ import annotations

import os
import random
import sys
import threading
import time
from pathlib import Path

from pymodbus.client import ModbusTcpClient

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import (  # noqa: E402
    DEVICE_ID,
    FIRMWARE_VERSION,
    SERVER_IP,
    is_client,
    is_server,
    json_log,
    jitter,
    malicious_ping,
)

MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "1502"))


def run_modbus_server() -> None:
    from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext  # noqa: E402
    from pymodbus.server import StartTcpServer  # noqa: E402

    store = ModbusSequentialDataBlock(0, [0] * 100)
    context = ModbusSlaveContext(hr=store, ir=store, di=store, co=store)
    server_context = ModbusServerContext(slaves=context, single=True)

    while True:
        try:
            json_log("modbus_server_start", port=MODBUS_PORT)
            StartTcpServer(server_context, host="0.0.0.0", port=MODBUS_PORT)
        except Exception as exc:  # noqa: BLE001
            json_log("modbus_server_error", error=str(exc))
            time.sleep(5)
        else:
            break


def run_modbus_client() -> None:
    client = ModbusTcpClient(SERVER_IP, port=MODBUS_PORT)
    if not client.connect():
        json_log("modbus_error", error="connect_failed")
        return
    try:
        while True:
            rr = client.read_holding_registers(0, 10, unit=1)
            registers = getattr(rr, "registers", "error")
            json_log("modbus_read", registers=registers)
            value = random.randint(0, 4095)
            client.write_register(5, value, unit=1)
            json_log("modbus_write", register=5, value=value)
            malicious_ping("/plc")
            time.sleep(jitter(20))
    finally:
        client.close()


def main() -> None:
    workers: list[threading.Thread] = []
    if is_server():
        server_thread = threading.Thread(target=run_modbus_server, daemon=True)
        server_thread.start()
        workers.append(server_thread)
    if is_client():
        run_modbus_client()
    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
