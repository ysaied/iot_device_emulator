#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

DEFAULT_REFRESH = int(os.environ.get("HUB_REFRESH_INTERVAL", "60"))
RETRY_INTERVAL = int(os.environ.get("HUB_RETRY_INTERVAL", "10"))
HUB_IP = os.environ.get("HUB_IP", "127.0.0.1")
HUB_PORT = os.environ.get("HUB_API_PORT", "7000")
DEVICE_ID = os.environ.get("DEVICE_ID", "device-unknown")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "UNKNOWN")
ROLE = os.environ.get("ROLE", "client")
IP_ADDRESS = os.environ.get("DEVICE_IP", "")
PROTOCOLS = os.environ.get("PERSONA_PRIMARY_PROTOCOLS", "[]")
MAC_ADDRESS = os.environ.get("MAC_ADDRESS", "")
FIRMWARE = os.environ.get("FIRMWARE_VERSION", "")
SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

PARENT_DIR = Path(__file__).resolve().parent


def log(event: str, **fields: str) -> None:
    payload = {"event": event, **fields}
    print(json.dumps(payload), flush=True)


def healthcheck() -> bool:
    url = f"http://{HUB_IP}:{HUB_PORT}/health"
    try:
        resp = SESSION.get(url, timeout=5)
        return resp.status_code == 200
    except requests.RequestException as exc:
        log("hub_health_failed", hub=HUB_IP, error=str(exc))
        return False


def register() -> bool:
    try:
        protocols = json.loads(PROTOCOLS) if PROTOCOLS else []
    except json.JSONDecodeError:
        protocols = []
    payload = {
        "device_id": DEVICE_ID,
        "device_type": DEVICE_TYPE,
        "role": ROLE,
        "ip_address": os.environ.get("DEVICE_IP", IP_ADDRESS),
        "protocols": protocols,
        "mac": MAC_ADDRESS,
        "firmware": FIRMWARE,
    }
    url = f"http://{HUB_IP}:{HUB_PORT}/register"
    try:
        resp = SESSION.post(url, data=json.dumps(payload), timeout=5)
        if resp.status_code == 200:
            log("hub_registered", hub=HUB_IP, status=resp.status_code)
            return True
        log("hub_register_error", hub=HUB_IP, status=resp.status_code, body=resp.text)
    except requests.RequestException as exc:
        log("hub_register_error", hub=HUB_IP, error=str(exc))
    return False


def main() -> None:
    while True:
        if not healthcheck():
            time.sleep(RETRY_INTERVAL)
            continue
        ip_addr = os.environ.get("DEVICE_IP") or IP_ADDRESS
        if not ip_addr:
            log("hub_register_error", hub=HUB_IP, error="missing_ip")
            time.sleep(RETRY_INTERVAL)
            continue
        if register():
            time.sleep(DEFAULT_REFRESH)
        else:
            time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()
