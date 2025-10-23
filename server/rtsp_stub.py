#!/usr/bin/env python3
from __future__ import annotations

import socketserver
import threading
from datetime import datetime


class RTSPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = self.request.recv(1024)
        message = data.decode(errors="ignore")
        response = (
            "RTSP/1.0 200 OK\r\n"
            f"CSeq: 1\r\n"
            f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
            "\r\n"
        )
        self.request.sendall(response.encode())
        print(f'{{"event":"rtsp_request","client":"{self.client_address[0]}","message":"{message.strip()}"}}', flush=True)


def serve_on(port: int) -> threading.Thread:
    server = socketserver.ThreadingTCPServer(("0.0.0.0", port), RTSPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f'{{"event":"rtsp_listen","port":{port}}}', flush=True)
    return thread


def main() -> None:
    threads = [serve_on(554), serve_on(8554)]
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
