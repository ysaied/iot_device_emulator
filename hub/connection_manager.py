#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
from pathlib import Path

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


def probe(host: str, port: int, protocol: str) -> None:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(
                json.dumps(
                    {"event": "hub_probe_success", "protocol": protocol, "host": host, "port": port}
                ),
                flush=True,
            )
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"event": "hub_probe_failed", "protocol": protocol, "host": host, "port": port, "error": str(exc)}
            ),
            flush=True,
        )


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
