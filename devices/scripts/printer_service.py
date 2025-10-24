#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import (  # noqa: E402
    DEVICE_ID,
    FIRMWARE_VERSION,
    is_server,
    json_log,
)

IPP_PORT = int(os.environ.get("IPP_PORT", "6310"))
SNMP_PORT = int(os.environ.get("SNMP_PORT", "16100"))
START_TIME = time.time()


class SimpleIPPHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode()) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body.decode(errors="ignore")}
        json_log("ipp_server_request", path=self.path, payload=payload)
        response = json.dumps({"status": "accepted"}).encode()
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
    from pysnmp.entity.rfc3413 import cmdrsp, context  # noqa: E402
    from pysnmp.smi import builder, rfc1902  # noqa: E402

    snmp_engine = engine.SnmpEngine()

    config.addTransport(
        snmp_engine,
        udp.domainName,
        udp.UdpTransport().openServerMode(("0.0.0.0", SNMP_PORT)),
    )
    config.addV1System(snmp_engine, "printer-agent", "public")
    config.addVacmUser(snmp_engine, 2, "printer-agent", "noAuthNoPriv", readSubTree=(1, 3, 6))
    snmp_context = context.SnmpContext(snmp_engine)

    mib_builder = snmp_engine.getMibBuilder()
    (MibScalarInstance,) = mib_builder.importSymbols("SNMPv2-SMI", "MibScalarInstance")
    sysDescr, sysUpTime = mib_builder.importSymbols("SNMPv2-MIB", "sysDescr", "sysUpTime")

    class SysDescrInstance(MibScalarInstance):
        def readGet(self, name, *args, **kwargs):
            json_log("snmp_server_request", oids=[str(name)], type="sysDescr")
            self.syntax = rfc1902.OctetString(f"Printer {DEVICE_ID} Firmware {FIRMWARE_VERSION}")
            return super().readGet(name, *args, **kwargs)

    class SysUpTimeInstance(MibScalarInstance):
        def readGet(self, name, *args, **kwargs):
            uptime = int((time.time() - START_TIME) * 100)
            json_log("snmp_server_request", oids=[str(name)], type="sysUpTime", uptime=uptime)
            self.syntax = rfc1902.TimeTicks(uptime)
            return super().readGet(name, *args, **kwargs)

    mib_builder.exportSymbols(
        "__PRINTER_MIB",
        SysDescrInstance(sysDescr.name, (0,), sysDescr.syntax.clone("")),
        SysUpTimeInstance(sysUpTime.name, (0,), sysUpTime.syntax.clone(0)),
    )

    cmdrsp.GetCommandResponder(snmp_engine, snmp_context)
    json_log("snmp_server_start", port=SNMP_PORT)
    try:
        snmp_engine.transportDispatcher.jobStarted(1)
        snmp_engine.transportDispatcher.runDispatcher()
    except Exception as exc:  # noqa: BLE001
        json_log("snmp_server_error", error=str(exc))
    finally:
        snmp_engine.transportDispatcher.closeDispatcher()


def main() -> None:
    if not is_server():
        json_log("printer_role_skip", reason="not_server")
        while True:
            time.sleep(60)

    threads = []
    ipp_thread = threading.Thread(target=run_ipp_server, daemon=True)
    ipp_thread.start()
    threads.append(ipp_thread)

    snmp_thread = threading.Thread(target=run_snmp_server, daemon=True)
    snmp_thread.start()
    threads.append(snmp_thread)

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
