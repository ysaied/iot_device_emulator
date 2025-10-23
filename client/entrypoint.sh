#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=false
DEBUG=false
for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=true ;;
    --debug) DEBUG=true ;;
  esac
done

if [[ "${DEBUG}" == "true" ]]; then
  set -x
fi

export PYTHONPATH="/opt/iot:${PYTHONPATH:-}"

log_json() {
  python3 - <<'PY' "$@"
import json
import sys

event = sys.argv[1]
payload = {"event": event}
for item in sys.argv[2:]:
    if "=" in item:
        key, value = item.split("=", 1)
        payload[key] = value
print(json.dumps(payload), flush=True)
PY
}

: "${DEVICE_TYPE:=CAMERA_RTSP}"
: "${DEVICE_ID:=device-$(date +%s)}"
: "${SERVER_IP:=127.0.0.1}"
: "${ENABLE_DHCLIENT:=true}"
: "${ENABLE_BROADCAST:=true}"
: "${ENABLE_PAIRING:=true}"
: "${DISCOVERY_INTENSITY:=low}"
: "${DHCP_TEMPLATE_PATH:=/opt/iot/configs/dhclient.jinja}"
: "${DHCP_TEMPLATE_DIR:=/opt/iot/client/dhclient-templates}"
: "${HOSTS_TEMPLATE_PATH:=/opt/iot/configs/hosts_map.template}"
: "${SAFE_MODE:=false}"

PERSONA_EXPORTS=$(python3 - <<'PY' "${DEVICE_TYPE}"
import json
import shlex
import sys
from pathlib import Path

import yaml

device_type = sys.argv[1]
profiles_path = Path("/opt/iot/client/profiles.yaml")
profiles = yaml.safe_load(profiles_path.read_text())
persona = profiles["personas"].get(device_type)
if not persona:
    print(f'echo "Unknown DEVICE_TYPE {device_type}" >&2; exit 1')
    sys.exit(0)

def emit(name, value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value)
    print(f"export {name}={shlex.quote(str(value))}")

emit("PERSONA_DISPLAY_NAME", persona.get("display_name", device_type))
emit("PERSONA_SCRIPT", persona.get("script", "device-scripts/heartbeat.py"))
emit("PERSONA_VENDOR_OUI", persona.get("vendor_oui", "00:11:22"))
emit("FIRMWARE_VERSION", persona.get("firmware_version", "0.0.0"))
emit("PERSONA_PROTOCOL", persona.get("protocol", "UNKNOWN"))
emit("PERSONA_PRIMARY_PROTOCOLS", persona.get("primary_protocols", []))
emit("PERSONA_PORTS", persona.get("ports", []))
emit("PERSONA_DHCP_HOSTNAME", persona["dhcp"]["hostname"])
emit("PERSONA_DHCP_VENDOR_CLASS", persona["dhcp"]["vendor_class"])
emit("PERSONA_DHCP_CLIENT_ID", persona["dhcp"]["client_id"])
emit("PERSONA_DISCOVERY_CHATTER", persona.get("discovery_chatter", []))
emit("PERSONA_PAIRING_CHATTER", persona.get("pairing_chatter", []))
emit("PAYLOAD_TEMPLATE", persona.get("payload_template", ""))
emit("VULNERABILITY_PROFILE", persona.get("vulnerability_profile", "none"))
PY
)

eval "${PERSONA_EXPORTS}"

if [[ -n "${VENDOR_OUI:-}" ]]; then
  PERSONA_VENDOR_OUI="${VENDOR_OUI}"
fi

log_json "persona_selected" device_type="${DEVICE_TYPE}" display_name="${PERSONA_DISPLAY_NAME}" firmware="${FIRMWARE_VERSION}"

MAC_ADDRESS="$(VENDOR_OUI="${PERSONA_VENDOR_OUI}" SAFE_MODE="${SAFE_MODE}" /opt/iot/client/common/macgen.sh)"

if [[ "${DRY_RUN}" == "true" ]]; then
  log_json "dry_run" mac="${MAC_ADDRESS}" dhcp_hostname="${PERSONA_DHCP_HOSTNAME}" vendor_class="${PERSONA_DHCP_VENDOR_CLASS}"
  exit 0
fi

if [[ "${SAFE_MODE}" != "true" ]]; then
  if ip link set dev eth0 address "${MAC_ADDRESS}"; then
    log_json "mac_applied" mac="${MAC_ADDRESS}"
  else
    log_json "mac_error" reason="cap_net_admin_required"
  fi
else
  log_json "mac_safe_mode" mac="${MAC_ADDRESS}"
fi

render_dhcp_conf() {
  python3 - <<'PY' "${DHCP_TEMPLATE_PATH}" "${PERSONA_DHCP_HOSTNAME}" "${PERSONA_DHCP_VENDOR_CLASS}" "${PERSONA_DHCP_CLIENT_ID}" "${DEVICE_ID}" "${FIRMWARE_VERSION}"
import sys
from pathlib import Path

from jinja2 import Template

template_path, hostname, vendor_class, client_id, device_id, firmware = sys.argv[1:7]
content = Path(template_path).read_text()
template = Template(content)
result = template.render(
    hostname=hostname.format(device_id=device_id),
    vendor_class=vendor_class.format(firmware_version=firmware),
    client_id=client_id.format(device_id=device_id),
)
Path("/etc/dhcp").mkdir(parents=True, exist_ok=True)
Path("/etc/dhcp/dhclient.conf").write_text(result)
print("OK")
PY
}

if [[ "${ENABLE_DHCLIENT}" == "true" ]]; then
  if render_dhcp_conf >/dev/null; then
    log_json "dhcp_conf_rendered"
    dhclient -v -1 eth0 || log_json "dhcp_error" reason="dhclient_failed"
    ip -4 addr show eth0
  else
    log_json "dhcp_conf_error"
  fi
else
  log_json "dhcp_skipped"
fi

if [[ -n "${HOSTNAME_MAP:-}" ]]; then
  IFS=',' read -r -a HOST_ARRAY <<<"${HOSTNAME_MAP}"
  {
    echo "127.0.0.1 localhost"
    for entry in "${HOST_ARRAY[@]}"; do
      if [[ "${entry}" == *"="* ]]; then
        host="${entry%%=*}"
        ip_value="${entry##*=}"
      else
        host="${entry}"
        ip_value="${SERVER_IP}"
      fi
      echo "${ip_value} ${host}"
    done
  } > /etc/hosts
  log_json "hosts_map_applied" entries="${HOSTNAME_MAP}"
fi

get_ip_address() {
  ip -o -4 addr show eth0 | awk '{print $4}' | cut -d/ -f1 | head -n1
}

DEVICE_IP="$(get_ip_address)"
if [[ -n "${DEVICE_IP}" ]]; then
  log_json "ip_acquired" ip="${DEVICE_IP}"
  curl -sf -X POST "http://${SERVER_IP}:9300/ingest" \
    -H "Content-Type: application/json" \
    -d "{\"event\":\"device_mapping\",\"mac\":\"${MAC_ADDRESS}\",\"device_type\":\"${DEVICE_TYPE}\",\"device_id\":\"${DEVICE_ID}\",\"firmware\":\"${FIRMWARE_VERSION}\",\"ip\":\"${DEVICE_IP}\"}" || \
    log_json "mapping_post_error" url="http://${SERVER_IP}:9300/ingest"
fi

if [[ "${ENABLE_BROADCAST}" == "true" ]]; then
  DISCOVERY_INTENSITY="${DISCOVERY_INTENSITY}" DEVICE_ID="${DEVICE_ID}" DEVICE_TYPE="${DEVICE_TYPE}" SERVER_IP="${SERVER_IP}" \
    /opt/iot/client/common/chatter_generator.sh &
  CHATTER_PID=$!
else
  CHATTER_PID=""
fi

pairing_probe() {
  python3 - <<'PY' "${ENABLE_PAIRING}" "${SERVER_IP}" "${DEVICE_ID}" "${PERSONA_PAIRING_CHATTER}" "${DEVICE_TYPE}"
import json
import os
import sys

enable, server_ip, device_id, chatter, device_type = sys.argv[1:6]
if enable.lower() != "true":
    sys.exit(0)
events = json.loads(chatter) if chatter else []
for event in events:
    print(json.dumps({"event": "pairing_probe", "device_id": device_id, "device_type": device_type, "probe": event, "server_ip": server_ip}))
PY
}

pairing_probe

SCRIPT_PATH="/opt/iot/client/device-scripts/${PERSONA_SCRIPT}"
if [[ ! -x "${SCRIPT_PATH}" ]]; then
  log_json "script_missing" path="${SCRIPT_PATH}"
  exit 1
fi

cleanup() {
  if [[ -n "${CHATTER_PID:-}" ]]; then
    kill "${CHATTER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export DEVICE_TYPE DEVICE_ID SERVER_IP FIRMWARE_VERSION VULNERABILITY_PROFILE MALICIOUS_MODE PAYLOAD_TEMPLATE

if [[ -n "${AUTOROTATE:-}" ]]; then
  log_json "autorotate_enabled" interval="${AUTOROTATE}"
  if ! command -v timeout >/dev/null 2>&1; then
    log_json "autorotate_disabled" reason="timeout-not-found"
    exec "${SCRIPT_PATH}"
  fi
  while true; do
    timeout "${AUTOROTATE}" "${SCRIPT_PATH}" || true
    sleep 2
  done
else
  exec "${SCRIPT_PATH}"
fi
