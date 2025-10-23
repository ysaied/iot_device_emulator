#!/usr/bin/env python3
"""
Helpers to apply vulnerability toggles to protocol clients.
"""

from __future__ import annotations

import base64
import hashlib
import random
from typing import Dict

from .vulnerability_toggles import VulnerabilityProfile


def apply_http_headers(
    headers: Dict[str, str],
    profile: VulnerabilityProfile,
    firmware_version: str,
) -> Dict[str, str]:
    mutated = dict(headers)
    if profile.weak_tls or profile.legacy_cipher:
        mutated["User-Agent"] = f"IOTDevice/{firmware_version} (TLSv1; Cipher=DES-CBC3-SHA)"
        mutated["X-TLS-Downgrade"] = "true"
    if profile.weak_creds:
        creds = base64.b64encode(b"admin:admin").decode()
        mutated["Authorization"] = f"Basic {creds}"
    if profile.attack_mode:
        mutated["X-Attack-Vector"] = random.choice(["dns-tunnel", "c2-beacon", "http-exfil"])
    return mutated


def mutate_mqtt_client_id(client_id: str, profile: VulnerabilityProfile, firmware_version: str) -> str:
    suffix = ""
    if profile.weak_tls:
        suffix = "_tls1"
    if profile.attack_mode:
        suffix += "_beacon"
    return f"{client_id}_{firmware_version.replace('.', '_')}{suffix}"


def legacy_cipher_suite(profile: VulnerabilityProfile) -> str | None:
    if profile.legacy_cipher:
        return "DES-CBC3-SHA"
    if profile.weak_tls:
        return "TLS_RSA_WITH_AES_128_CBC_SHA"
    return None


def malicious_query_name(device_id: str, profile: VulnerabilityProfile) -> str | None:
    if not profile.attack_mode:
        return None
    digest = hashlib.sha1(device_id.encode()).hexdigest()[:12]
    return f"{digest}.exfil.lab"
