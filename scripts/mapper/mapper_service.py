#!/usr/bin/env python3
"""
Mapper service that builds MAC -> identity table by consuming server logs.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict

SERVER_IP = os.environ.get("SERVER_IP", "127.0.0.1")
LOG_ENDPOINT = os.environ.get("LOG_ENDPOINT", f"http://{SERVER_IP}:9300/logs")
OUTPUT_PATH = Path(os.environ.get("MAPPINGS_PATH", "/data/mappings.json"))
POLL_INTERVAL = float(os.environ.get("MAPPER_POLL_INTERVAL", "10"))


def fetch_logs() -> dict:
    import requests

    response = requests.get(LOG_ENDPOINT, timeout=5)
    response.raise_for_status()
    return response.json()


def build_mapping(logs: dict) -> Dict[str, dict]:
    entries = logs.get("logs", [])
    mapping: Dict[str, dict] = {}
    for entry in entries:
        if entry.get("event") != "device_mapping":
            continue
        mac = entry.get("mac")
        if not mac:
            continue
        mapping[mac] = {
            "device_type": entry.get("device_type"),
            "device_id": entry.get("device_id"),
            "firmware_version": entry.get("firmware"),
            "ip": entry.get("ip"),
            "timestamp": entry.get("timestamp", time.time()),
        }
    return mapping


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            logs = fetch_logs()
            mapping = build_mapping(logs)
            OUTPUT_PATH.write_text(json.dumps(mapping, indent=2))
            print(
                json.dumps(
                    {"event": "mapping_update", "count": len(mapping), "path": str(OUTPUT_PATH)}
                ),
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"event": "mapping_error", "error": str(exc)}), flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
