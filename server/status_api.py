#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI

app = FastAPI(title="IoT Emulator Status API")

LOG_FILE = Path("/data/logs/events.log")
MAPPINGS_FILE = Path("/data/mappings.json")


def read_logs(limit: int = 200) -> List[Dict[str, Any]]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open() as fh:
        lines = fh.readlines()[-limit:]
    results = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def protocol_summary(logs: List[Dict[str, Any]]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for entry in logs:
        event = entry.get("event")
        if not event:
            continue
        if "mqtt" in event:
            counter["mqtt"] += 1
        elif "modbus" in event:
            counter["modbus"] += 1
        elif "rtsp" in event:
            counter["rtsp"] += 1
        elif "sip" in event:
            counter["sip"] += 1
        elif "dicom" in event:
            counter["dicom"] += 1
        elif "snmp" in event:
            counter["snmp"] += 1
        elif "coap" in event:
            counter["coap"] += 1
        elif "bacnet" in event:
            counter["bacnet"] += 1
    return dict(counter)


def load_mappings() -> Dict[str, Any]:
    if not MAPPINGS_FILE.exists():
        return {}
    try:
        return json.loads(MAPPINGS_FILE.read_text())
    except json.JSONDecodeError:
        return {}


@app.get("/status")
def status() -> Dict[str, Any]:
    logs = read_logs()
    return {
        "timestamp": time.time(),
        "active_protocols": protocol_summary(logs),
        "recent_logs": logs[-20:],
        "mappings": load_mappings(),
    }


@app.get("/status/mappings")
def status_mappings() -> Dict[str, Any]:
    return load_mappings()


@app.get("/status/logs")
def status_logs() -> Dict[str, Any]:
    logs = read_logs()
    return {"logs": logs}
