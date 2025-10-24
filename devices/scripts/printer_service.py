#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List

import requests
from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import (  # noqa: E402
    DEVICE_ID,
    FIRMWARE_VERSION,
    HUB_IP,
    SERVER_IP,
    is_client,
    is_server,
    json_log,
    jitter,
    malicious_ping,
)

IPP_PORT = int(os.environ.get("IPP_PORT", "6310"))
SNMP_PORT = int(os.environ.get("SNMP_PORT", "16100"))


def send_ipp_status() -> None:
    url = f"http://{SERVER_IP}:{IPP_PORT}/ipp/printer"
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
    target_ip = HUB_IP or SERVER_IP
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData("public"),
            UdpTransportTarget((target_ip, SNMP_PORT), timeout=2, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
        )
        response = next(iterator)
    except StopIteration:
        json_log("snmp_error", error="no_response")
        return
    except Exception as exc:  # noqa: BLE001
        json_log("snmp_error", error=str(exc))
        return

    error_indication, error_status, _, var_binds = response
    if error_indication:
        json_log("snmp_error", error=str(error_indication))
        return
    if error_status:
        json_log("snmp_error", error=str(error_status.prettyPrint()))
        return

    for var_bind in var_binds:
        json_log("snmp_response", value=" = ".join([x.prettyPrint() for x in var_bind]))


def run_client() -> None:
    while True:
        send_ipp_status()
        poll_snmp()
        malicious_ping("/printer")
        time.sleep(jitter(20))


class SimpleIPPHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode()) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body.decode(errors="ignore")}
        json_log("ipp_server_request", path=self.path, payload=payload)
        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run_ipp_server() -> None:
    server = HTTPServer(("0.0.0.0", IPP_PORT), SimpleIPPHandler)
    json_log("ipp_server_start", port=IPP_PORT)
    try:
        server.serve_forever()
    except Exception as exc:  # noqa: BLE001
        json_log("ipp_server_error", error=str(exc))


def run_snmp_server() -> None:
    from pysnmp.carrier.asyncore.dgram import udp  # noqa: E402
    from pysnmp.entity import config, engine  # noqa: E402
    from pysnmp.entity.rfc3413 import cmdrsp  # noqa: E402
    from pysnmp.proto import rfc1905  # noqa: E402
    from pysnmp.smi import rfc1902  # noqa: E402

    snmp_engine = engine.SnmpEngine()

    config.addTransport(
        snmp_engine,
        udp.domainName,
        udp.UdpTransport().openServerMode(("0.0.0.0", SNMP_PORT)),
    )
    config.addV1System(snmp_engine, "printer-agent", "public")
    config.addVacmUser(snmp_engine, 1, "printer-agent", "noAuthNoPriv", readSubTree=(1, 3, 6))
    config.addVacmUser(snmp_engine, 2, "printer-agent", "noAuthNoPriv", readSubTree=(1, 3, 6))
    config.addContext(snmp_engine, "")

    def cb_fun(snmp_engine, state_reference, context_engine_id, context_name, var_binds, cb_ctx):  # noqa: ANN001
        oids: List[str] = []
        for idx, (name, value) in enumerate(var_binds):
            oid_str = str(name)
            oids.append(oid_str)
            if oid_str == "1.3.6.1.2.1.1.1.0":
                var_binds[idx] = (
                    name,
                    rfc1902.OctetString(f"Printer {DEVICE_ID} Firmware {FIRMWARE_VERSION}"),
                )
            elif oid_str == "1.3.6.1.2.1.1.3.0":
                var_binds[idx] = (name, rfc1902.TimeTicks(int(time.time() * 100)))
            else:
                var_binds[idx] = (name, rfc1905.NoSuchObject())
        json_log("snmp_server_request", oids=oids)

    cmdrsp.GetCommandResponder(snmp_engine, cb_fun)
    json_log("snmp_server_start", port=SNMP_PORT)
    snmp_engine.transportDispatcher.jobStarted(1)
    try:
        snmp_engine.transportDispatcher.runDispatcher()
    except Exception as exc:  # noqa: BLE001
        json_log("snmp_server_error", error=str(exc))
    finally:
        snmp_engine.transportDispatcher.closeDispatcher()


def main() -> None:
    workers: list[threading.Thread] = []
    if is_server():
        ipp_thread = threading.Thread(target=run_ipp_server, daemon=True)
        ipp_thread.start()
        workers.append(ipp_thread)
        snmp_thread = threading.Thread(target=run_snmp_server, daemon=True)
        snmp_thread.start()
        workers.append(snmp_thread)
    if is_client():
        run_client()
    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
