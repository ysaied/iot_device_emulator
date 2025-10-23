#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List

DATA_DIR = Path("/data/logs")
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "events.log"


def append_log(entry: dict) -> None:
    with LOG_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    print(json.dumps({"event": "log_ingest", **entry}), flush=True)


def tail_logs(limit: int = 100) -> List[dict]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open() as fh:
        lines = fh.readlines()[-limit:]
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


class LogHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/ingest", "/log"):
            self.send_error(404, "Not Found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        append_log(payload)
        self.send_response(202)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/logs"):
            logs = tail_logs()
            data = json.dumps({"logs": logs}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 9300), LogHandler)
    print('{"event":"logshipper_listen","port":9300}', flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
