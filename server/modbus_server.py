#!/usr/bin/env python3
from __future__ import annotations

import logging

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO)


def build_context() -> ModbusServerContext:
    store = ModbusSequentialDataBlock(0, [0] * 100)
    context = ModbusSlaveContext(hr=store, ir=store, di=store, co=store)
    return ModbusServerContext(slaves=context, single=True)


def main() -> None:
    context = build_context()
    logging.info("Starting Modbus/TCP server on 0.0.0.0:502")
    StartTcpServer(context, address=("0.0.0.0", 502))


if __name__ == "__main__":
    main()
