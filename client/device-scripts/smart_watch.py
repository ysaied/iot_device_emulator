#!/usr/bin/env python3
from __future__ import annotations

import time

import requests

from .common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def push_metrics() -> None:
    payload = {
        "device_id": DEVICE_ID,
        "firmware": FIRMWARE_VERSION,
        "steps": int(5000 + jitter(1000)),
        "heart_rate": 70 + int(jitter(10)),
    }
    try:
        resp = requests.post(
            f"https://{SERVER_IP}/wearable/metrics",
            json=payload,
            timeout=5,
            verify=False,
        )
        json_log("https_metrics", status=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("https_error", error=str(exc))


def main() -> None:
    while True:
        push_metrics()
        malicious_ping("/watch")
        time.sleep(jitter(15))


if __name__ == "__main__":
    main()
