#!/usr/bin/env python3
from __future__ import annotations

import time

import requests
from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectType,
    ObjectIdentity,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

from .common import (
    DEVICE_ID,
    FIRMWARE_VERSION,
    SERVER_IP,
    json_log,
    jitter,
    malicious_ping,
)


def send_ipp_status() -> None:
    url = f"http://{SERVER_IP}:631/ipp/printer"
    payload = {
        "device_id": DEVICE_ID,
        "firmware": FIRMWARE_VERSION,
        "status": "idle",
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        json_log("ipp_status", status_code=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("ipp_error", error=str(exc))


def poll_snmp() -> None:
    iterator = getCmd(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget((SERVER_IP, 161)),
        ContextData(),
        ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
    )
    error_indication, error_status, _, var_binds = next(iterator)
    if error_indication:
        json_log("snmp_error", error=str(error_indication))
    elif error_status:
        json_log("snmp_error", error=str(error_status.prettyPrint()))
    else:
        for var_bind in var_binds:
            json_log("snmp_response", value=" = ".join([x.prettyPrint() for x in var_bind]))


def main() -> None:
    while True:
        send_ipp_status()
        poll_snmp()
        malicious_ping("/printer")
        time.sleep(jitter(20))


if __name__ == "__main__":
    main()
