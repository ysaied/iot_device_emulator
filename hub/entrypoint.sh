#!/usr/bin/env bash
set -euo pipefail

export REGISTRY_DB_PATH="${REGISTRY_DB_PATH:-/data/hub_registry.db}"
export HUB_API_PORT="${HUB_API_PORT:-7000}"

python3 -m uvicorn registry_service:app --host 0.0.0.0 --port "${HUB_API_PORT}" &
REGISTRY_PID=$!

python3 connection_manager.py &
CONN_PID=$!

trap 'kill ${REGISTRY_PID} ${CONN_PID}' INT TERM
wait ${REGISTRY_PID} ${CONN_PID}
