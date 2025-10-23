#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import sys
import time

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def build_context() -> ModbusServerContext:
    store = ModbusSequentialDataBlock(0, [0] * 100)
    context = ModbusSlaveContext(hr=store, ir=store, di=store, co=store)
    return ModbusServerContext(slaves=context, single=True)


def main() -> None:
    port = int(os.environ.get("MODBUS_PORT", "1502"))
    context = build_context()
    while True:
        try:
            logging.info("Starting Modbus/TCP server on 0.0.0.0:%s", port)
            StartTcpServer(context, host="0.0.0.0", port=port)
        except Exception as exc:  # noqa: BLE001
            logging.error("Modbus server error: %s", exc)
            time.sleep(5)
        else:
            break


if __name__ == "__main__":
    main()
