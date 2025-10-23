#!/usr/bin/env python3
"""
Helper to spawn multiple IoT client containers with varying personas.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys


DEFAULT_PERSONAS = [
    "CAMERA_RTSP",
    "PRINTER_SERVICE",
    "IP_PHONE_SIP",
    "SMART_TV",
    "SMART_SPEAKER",
    "THERMOSTAT_MQTT",
    "SMART_PLUG_COAP",
    "PLC_MODBUS",
    "SCADA_SENSOR",
    "ECG_MQTT",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spawn IoT client containers.")
    parser.add_argument("--image", default="iot-client", help="Client image name")
    parser.add_argument("--server-ip", required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--network", default=None, help="Docker network to attach")
    parser.add_argument("--device-types", nargs="*", default=DEFAULT_PERSONAS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def build_command(args: argparse.Namespace, index: int, device_type: str) -> list[str]:
    device_id = f"{device_type.lower()}-{index:02d}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--cap-add=NET_ADMIN",
        "--env", f"DEVICE_TYPE={device_type}",
        "--env", f"DEVICE_ID={device_id}",
        "--env", f"SERVER_IP={args.server_ip}",
        args.image,
    ]
    if args.network:
        cmd.extend(["--network", args.network])
    return cmd


def main() -> None:
    args = parse_args()
    for index in range(args.count):
        device_type = random.choice(args.device_types)
        cmd = build_command(args, index, device_type)
        if args.dry_run:
            print(" ".join(cmd))
            continue
        print(f"Launching {device_type} -> {' '.join(cmd)}")
        subprocess.Popen(cmd)


if __name__ == "__main__":
    if not sys.platform.startswith("linux"):
        print("Spawner is best effort on non-Linux hosts.", file=sys.stderr)
    main()
