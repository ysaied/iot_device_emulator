#!/usr/bin/env python3
from __future__ import annotations

import socket


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5060))
    print('{"event":"sip_listen","port":5060}', flush=True)
    while True:
        data, addr = sock.recvfrom(2048)
        message = data.decode(errors="ignore")
        print(f'{{"event":"sip_message","from":"{addr[0]}","message":"{message.strip()}"}}', flush=True)
        sock.sendto(b"SIP/2.0 200 OK\r\n\r\n", addr)


if __name__ == "__main__":
    main()
