#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import ssl
import time

import requests

from client.common.vulnerability_toggles import get_profile
from client.common.vuln_injector import apply_http_headers, legacy_cipher_suite

from .common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


PROFILE = get_profile(os.environ.get("VULNERABILITY_PROFILE", "none"))


def send_ssdp() -> None:
    message = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        "MX: 2\r\n"
        "ST: urn:schemas-upnp-org:device:SmartTV:1\r\n\r\n"
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.sendto(message.encode(), ("239.255.255.250", 1900))
    sock.close()
    json_log("ssdp_discover")


def http_interactions() -> None:
    headers = apply_http_headers({"User-Agent": f"SmartTV/{FIRMWARE_VERSION}"}, PROFILE, FIRMWARE_VERSION)
    try:
        resp = requests.get(f"http://{SERVER_IP}/status/tv", headers=headers, timeout=5)
        json_log("http_status", status_code=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        json_log("http_error", error=str(exc))

    try:
        resp = requests.get(f"https://{SERVER_IP}/status/tv", headers=headers, timeout=5, verify=False)
        json_log("https_status", status_code=resp.status_code, verify="false")
    except Exception as exc:  # noqa: BLE001
        json_log("https_error", error=str(exc))


def tls_handshake() -> None:
    cipher = legacy_cipher_suite(PROFILE)
    context = ssl.create_default_context()
    if cipher:
        context.set_ciphers(cipher)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((SERVER_IP, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=SERVER_IP) as tls_sock:
                tls_sock.send(b"HEAD /status HTTP/1.1\r\nHost: server\r\n\r\n")
                json_log("tls_handshake", cipher=tls_sock.cipher())
    except Exception as exc:  # noqa: BLE001
        json_log("tls_error", error=str(exc))


def main() -> None:
    while True:
        send_ssdp()
        http_interactions()
        tls_handshake()
        malicious_ping("/tv")
        time.sleep(jitter(25))


if __name__ == "__main__":
    main()
