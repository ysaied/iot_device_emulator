#!/usr/bin/env python3
"""
Helper utilities shared across persona device scripts.
"""

from __future__ import annotations

import json
import os
import random
import socket
import sys
import time
from typing import Any, Dict


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DEVICE_ID = env("DEVICE_ID", "device-unknown")
SERVER_IP = env("SERVER_IP", "127.0.0.1")
FIRMWARE_VERSION = env("FIRMWARE_VERSION", "0.0.0")
DEVICE_TYPE = env("DEVICE_TYPE", "UNKNOWN")
MALICIOUS_MODE = env("MALICIOUS_MODE", "false").lower() == "true"


def json_log(event: str, **fields: Any) -> None:
    payload: Dict[str, Any] = {
        "event": event,
        "timestamp": time.time(),
        "device_id": DEVICE_ID,
        "device_type": DEVICE_TYPE,
        "firmware_version": FIRMWARE_VERSION,
        **fields,
    }
    print(json.dumps(payload), flush=True)


def open_tcp_socket(port: int, timeout: float = 5.0) -> socket.socket:
    sock = socket.create_connection((SERVER_IP, port), timeout=timeout)
    return sock


def jitter(base: float, variance: float = 0.2) -> float:
    return max(0.1, random.uniform(base * (1 - variance), base * (1 + variance)))


def malicious_ping(endpoint: str = "/beacon") -> None:
    if not MALICIOUS_MODE:
        return
    try:
        with open_tcp_socket(8080) as sock:
            payload = f"POST {endpoint} HTTP/1.1\r\nHost: {SERVER_IP}\r\nContent-Length: 0\r\n\r\n"
            sock.sendall(payload.encode())
            json_log("malicious_beacon", endpoint=endpoint, status="sent")
    except Exception as exc:  # noqa: BLE001
        json_log("malicious_beacon_error", error=str(exc))


def heartbeat_loop(interval: float):
    """Simple heartbeat generator for scripts that do not implement custom loops."""
    try:
        while True:
            json_log("heartbeat")
            malicious_ping()
            time.sleep(jitter(interval))
    except KeyboardInterrupt:
        json_log("shutdown")


if __name__ == "__main__":
    heartbeat_loop(30.0)
