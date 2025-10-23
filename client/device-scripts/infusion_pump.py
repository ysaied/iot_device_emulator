#!/usr/bin/env python3
from __future__ import annotations

import json
import time

import paho.mqtt.client as mqtt
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
    error = sendNotification(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget((SERVER_IP, 162)),
        ContextData(),
        "trap",
        NotificationType(ObjectIdentity("1.3.6.1.4.1.4976.10.1")).addVarBinds(
            ("1.3.6.1.4.1.4976.10.2", DEVICE_ID),
            ("1.3.6.1.4.1.4976.10.3", FIRMWARE_VERSION),
        ),
    )
    if error:
        json_log("snmp_trap_error", error=str(error))
    else:
        json_log("snmp_trap_sent")


def http_update() -> None:
    payload = {
        "device_id": DEVICE_ID,
        "firmware": FIRMWARE_VERSION,
        "rate_ml_hr": round(20 + jitter(5), 2),
    }
    try:
        resp = requests.post(f"https://{SERVER_IP}/pump/update", json=payload, timeout=5, verify=False)
        json_log("http_update", status=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("http_error", error=str(exc))


def mqtt_publish(client: mqtt.Client) -> None:
    payload = {
        "device_id": DEVICE_ID,
        "firmware": FIRMWARE_VERSION,
        "volume_remaining_ml": round(150 + jitter(20), 2),
    }
    client.publish(f"pump/{DEVICE_ID}/telemetry", json.dumps(payload))
    json_log("mqtt_publish")


def main() -> None:
    client = mqtt.Client(client_id=f"{DEVICE_ID}-pump")
    client.connect(SERVER_IP, 1883, keepalive=60)
    client.loop_start()
    try:
        while True:
            send_snmp_trap()
            http_update()
            mqtt_publish(client)
            malicious_ping("/pump")
            time.sleep(jitter(30))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
