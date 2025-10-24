#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = Path(os.environ.get("REGISTRY_DB_PATH", "/data/hub_registry.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="IoT Hub Registry")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT,
                role TEXT,
                ip_address TEXT,
                protocols TEXT,
                last_seen REAL
            )
            """
        )
        conn.commit()


class Registration(BaseModel):
    device_id: str
    device_type: str
    role: str
    ip_address: str
    protocols: List[str] = []


@app.on_event("startup")
async def startup_event() -> None:
    init_db()


@app.post("/register")
async def register_device(payload: Registration) -> dict[str, str]:
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO devices(device_id, device_type, role, ip_address, protocols, last_seen)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                device_type=excluded.device_type,
                role=excluded.role,
                ip_address=excluded.ip_address,
                protocols=excluded.protocols,
                last_seen=excluded.last_seen
            """,
            (
                payload.device_id,
                payload.device_type,
                payload.role,
                payload.ip_address,
                json.dumps(payload.protocols),
                now,
            ),
        )
        conn.commit()
    return {"status": "registered", "device_id": payload.device_id}


@app.get("/devices")
async def list_devices() -> list[dict[str, object]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT device_id, device_type, role, ip_address, protocols, last_seen FROM devices"
        ).fetchall()
    return [
        {
            "device_id": row[0],
            "device_type": row[1],
            "role": row[2],
            "ip_address": row[3],
            "protocols": json.loads(row[4]) if row[4] else [],
            "last_seen": row[5],
        }
        for row in rows
    ]


@app.get("/devices/{device_id}")
async def get_device(device_id: str) -> dict[str, object]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT device_id, device_type, role, ip_address, protocols, last_seen FROM devices WHERE device_id=?",
            (device_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="device not found")
    return {
        "device_id": row[0],
        "device_type": row[1],
        "role": row[2],
        "ip_address": row[3],
        "protocols": json.loads(row[4]) if row[4] else [],
        "last_seen": row[5],
    }


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("registry_service:app", host="0.0.0.0", port=int(os.environ.get("HUB_API_PORT", "7000")))
