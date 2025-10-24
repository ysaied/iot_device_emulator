#!/usr/bin/env python3
"""
Generate persona payloads with light randomness for telemetry realism.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict


PLACEHOLDER_PREFIX = "{"


def _random_choice(values: str) -> str:
    options = [item.strip() for item in values.split(",") if item.strip()]
    return random.choice(options)


def _random_waveform(kind: str) -> Dict[str, Any]:
    length = 20
    if kind == "sinus":
        return {
            "type": "sinus",
            "samples": [
                round(math.sin((i / length) * math.tau) * 1.0 + random.uniform(-0.05, 0.05), 3)
                for i in range(length)
            ],
        }
    if kind == "square":
        return {
            "type": "square",
            "samples": [1 if (i // 5) % 2 == 0 else -1 for i in range(length)],
        }
    return {"type": kind, "samples": [0.0] * length}


def _render_placeholder(token: str, context: Dict[str, Any]) -> Any:
    if token == "device_id":
        return context.get("device_id")
    if token == "firmware_version":
        return context.get("firmware_version")
    if token == "server_ip":
        return context.get("server_ip")
    if token == "uptime":
        return int(time.time() - context.get("start_time", time.time()))
    if token == "uuid":
        return str(uuid.uuid4())
    if token.startswith("randint:"):
        low, high = token.split(":", 1)[1].split("-")
        return random.randint(int(low), int(high))
    if token.startswith("randfloat:"):
        low, high = token.split(":", 1)[1].split("-")
        return round(random.uniform(float(low), float(high)), 3)
    if token.startswith("choice:"):
        return _random_choice(token.split(":", 1)[1])
    if token.startswith("waveform:"):
        return _random_waveform(token.split(":", 1)[1])
    return context.get(token, token)


def _render_value(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIX) and value.endswith("}"):
        token = value[1:-1]
        return _render_placeholder(token, context)
    if isinstance(value, list):
        return [_render_value(item, context) for item in value]
    if isinstance(value, dict):
        return {key: _render_value(val, context) for key, val in value.items()}
    return value


def build_payload(template_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
    raw = json.loads(template_path.read_text())
    context = dict(context)
    context.setdefault("start_time", time.time())
    rendered = {key: _render_value(val, context) for key, val in raw.items()}
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate persona telemetry payload.")
    parser.add_argument("--template", required=True, type=Path, help="Path to payload template JSON")
    parser.add_argument("--device-type", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--firmware-version", required=True)
    parser.add_argument("--server-ip", default="127.0.0.1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(
        args.template,
        {
            "device_type": args.device_type,
            "device_id": args.device_id,
            "firmware_version": args.firmware_version,
            "server_ip": args.server_ip,
        },
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
