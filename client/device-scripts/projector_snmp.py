#!/usr/bin/env python3
from __future__ import annotations

import time

import requests
from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    NotificationType,
    ObjectIdentity,
    SnmpEngine,
    UdpTransportTarget,
    sendNotification,
)

from .common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def send_snmp_trap() -> None:
    error_indication = sendNotification(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget((SERVER_IP, 162)),
        ContextData(),
        "trap",
        NotificationType(ObjectIdentity("1.3.6.1.4.1.32473.1.0")).addVarBinds(
            ("1.3.6.1.4.1.32473.1.1.1", DEVICE_ID),
            ("1.3.6.1.4.1.32473.1.1.2", FIRMWARE_VERSION),
        ),
    )
    if error_indication:
        json_log("snmp_trap_error", error=str(error_indication))
    else:
        json_log("snmp_trap_sent")


def http_config_check() -> None:
    try:
        resp = requests.get(f"http://{SERVER_IP}/projector/config", timeout=5)
        json_log("http_config", status=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("http_error", error=str(exc))


def main() -> None:
    while True:
        send_snmp_trap()
        http_config_check()
        malicious_ping("/projector")
        time.sleep(jitter(45))


if __name__ == "__main__":
    main()
