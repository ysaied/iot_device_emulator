#!/usr/bin/env python3
from __future__ import annotations

import random
import socket
import time

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def send_register(seq: int) -> None:
    message = (
        f"REGISTER sip:{SERVER_IP} SIP/2.0\r\n"
        f"Via: SIP/2.0/UDP {DEVICE_ID}.lab;branch=z9hG4bK-{seq}\r\n"
        f"From: <sip:{DEVICE_ID}@lab>\r\n"
        f"To: <sip:{DEVICE_ID}@lab>\r\n"
        f"Call-ID: {DEVICE_ID}-{seq}@lab\r\n"
        f"CSeq: {seq} REGISTER\r\n"
        f"Contact: <sip:{DEVICE_ID}@{DEVICE_ID}.lab>\r\n"
        f"User-Agent: VoipPhone/{FIRMWARE_VERSION}\r\n"
        "Max-Forwards: 70\r\n"
        "Content-Length: 0\r\n\r\n"
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode(), (SERVER_IP, 5060))
    sock.close()
    json_log("sip_register", cseq=seq)


def send_keepalive() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = b"\x80"
    sock.sendto(payload, (SERVER_IP, random.randint(16384, 16484)))
    sock.close()
    json_log("rtp_keepalive")


def main() -> None:
    seq = 1
    while True:
        send_register(seq)
        send_keepalive()
        malicious_ping("/sip")
        seq += 1
        time.sleep(jitter(30))


if __name__ == "__main__":
    main()
