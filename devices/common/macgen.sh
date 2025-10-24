#!/usr/bin/env bash
set -euo pipefail

: "${VENDOR_OUI:=}"
REGISTRY_FILE="${MAC_REGISTRY_FILE:-/var/lib/iot-macs/assigned_macs.txt}"

if [[ -z "${VENDOR_OUI}" ]]; then
  echo "macgen: VENDOR_OUI is required" >&2
  exit 1
fi

if ! [[ "${VENDOR_OUI}" =~ ^([0-9A-Fa-f]{2}:){2}[0-9A-Fa-f]{2}$ ]]; then
  echo "macgen: invalid VENDOR_OUI format (${VENDOR_OUI})" >&2
  exit 1
fi

generate_suffix() {
  printf "%02X:%02X:%02X" "$((RANDOM % 256))" "$((RANDOM % 256))" "$((RANDOM % 256))"
}

ensure_registry() {
  local dir
  dir="$(dirname "${REGISTRY_FILE}")"
  mkdir -p "${dir}"
  touch "${REGISTRY_FILE}"
}

ensure_registry

attempts=0
max_attempts=20
mac=""
while (( attempts < max_attempts )); do
  suffix="$(generate_suffix)"
  mac="${VENDOR_OUI^^}:${suffix}"
  if ! grep -qi "^${mac}$" "${REGISTRY_FILE}"; then
    break
  fi
  attempts=$((attempts + 1))
done

if (( attempts >= max_attempts )); then
  echo "macgen: exhausted attempts to create unique MAC" >&2
  exit 1
fi

if [[ "${SAFE_MODE:-false}" != "true" ]]; then
  echo "${mac}" >> "${REGISTRY_FILE}"
fi

echo "${mac}"
