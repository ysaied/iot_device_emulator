#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
from pathlib import Path

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

DB_PATH = Path(os.environ.get("REGISTRY_DB_PATH", "/data/hub_registry.db"))
POLL_INTERVAL = int(os.environ.get("HUB_POLL_INTERVAL", "20"))

PROTOCOL_PORTS = {
    "ModbusTCP": int(os.environ.get("MODBUS_PORT", "1502")),
    "DICOM": int(os.environ.get("DICOM_PORT", "11112")),
    "RTSP": int(os.environ.get("RTSP_PORT", "8554")),
    "IPP": int(os.environ.get("IPP_PORT", "6310")),
    "SNMP": int(os.environ.get("SNMP_PORT", "16100")),
}


def fetch_devices() -> list[dict[str, object]]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT device_id, device_type, role, ip_address, protocols, last_seen FROM devices"
        ).fetchall()
    devices = []
    for row in rows:
        protocols = json.loads(row[4]) if row[4] else []
        devices.append(
            {
                "device_id": row[0],
                "device_type": row[1],
                "role": row[2],
                "ip_address": row[3],
                "protocols": protocols,
                "last_seen": row[5],
            }
        )
    return devices


def log_event(event: str, **fields: str) -> None:
    print(json.dumps({"event": event, **fields}), flush=True)


def probe_tcp(host: str, port: int, protocol: str) -> None:
    try:
        with socket.create_connection((host, port), timeout=3):
            log_event("hub_probe_success", protocol=protocol, host=host, port=port)
    except Exception as exc:  # noqa: BLE001
        log_event("hub_probe_failed", protocol=protocol, host=host, port=port, error=str(exc))


def probe_snmp(host: str, port: int) -> None:
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData("public", mpModel=1),
            UdpTransportTarget((host, port), timeout=2, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
        )
        error_indication, error_status, _, var_binds = next(iterator)
        if error_indication:
            log_event(
                "hub_probe_failed",
                protocol="SNMP",
                host=host,
                port=port,
                error=str(error_indication),
            )
            return
        if error_status:
            log_event(
                "hub_probe_failed",
                protocol="SNMP",
                host=host,
                port=port,
                error=str(error_status.prettyPrint()),
            )
            return
        value = " = ".join([x.prettyPrint() for x in var_binds[0]]) if var_binds else "ok"
        log_event("hub_probe_success", protocol="SNMP", host=host, port=port, value=value)
    except Exception as exc:  # noqa: BLE001
        log_event("hub_probe_failed", protocol="SNMP", host=host, port=port, error=str(exc))


def probe(host: str, port: int, protocol: str) -> None:
    if protocol == "SNMP":
        probe_snmp(host, port)
    else:
        probe_tcp(host, port, protocol)


def main() -> None:
    while True:
        for device in fetch_devices():
            if device["role"] not in {"server", "both"}:
                continue
            host = device["ip_address"]
            for protocol in device["protocols"]:
                port = PROTOCOL_PORTS.get(protocol)
                if port:
                    probe(host, port, protocol)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
