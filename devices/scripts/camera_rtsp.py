#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import (  # noqa: E402
    DEVICE_ID,
    FIRMWARE_VERSION,
    SERVER_IP,
    is_client,
    is_server,
    json_log,
    malicious_ping,
)

RTSP_SERVER_PORT = int(os.environ.get("RTSP_PORT", "8554"))


def run_rtsp_server() -> None:
    import socketserver

    class RTSPHandler(socketserver.BaseRequestHandler):
        def handle(self) -> None:  # noqa: D401
            data = self.request.recv(1024)
            message = data.decode(errors="ignore")
            response = (
                "RTSP/1.0 200 OK\r\n"
                f"CSeq: 1\r\n"
                f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
                "\r\n"
            )
            self.request.sendall(response.encode())
            json_log("rtsp_server_request", client=self.client_address[0], payload=message.strip())

    class ThreadedServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    server = ThreadedServer(("0.0.0.0", RTSP_SERVER_PORT), RTSPHandler)
    json_log("rtsp_server_start", port=RTSP_SERVER_PORT)
    server.serve_forever()


def run_rtsp_client() -> None:
    target = SERVER_IP
    message = (
        "OPTIONS rtsp://{0}:{1}/stream/{2} RTSP/1.0\r\n"
        "CSeq: 1\r\n"
        "User-Agent: Camera/{3}\r\n\r\n"
    ).format(target, RTSP_SERVER_PORT, DEVICE_ID, FIRMWARE_VERSION)
    while True:
        try:
            with socket.create_connection((target, RTSP_SERVER_PORT), timeout=5) as sock:
                sock.sendall(message.encode())
                json_log("rtsp_keepalive", status="sent")
        except Exception as exc:  # noqa: BLE001
            json_log("rtsp_client_error", error=str(exc))
        malicious_ping("/camera")
        time.sleep(15)


def main() -> None:
    threads: list[threading.Thread] = []
    if is_server():
        server_thread = threading.Thread(target=run_rtsp_server, daemon=True)
        server_thread.start()
        threads.append(server_thread)
    if is_client():
        run_rtsp_client()
    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
