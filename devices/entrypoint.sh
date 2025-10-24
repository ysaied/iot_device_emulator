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

PREFERRED_SOURCE_IP=""

detect_preferred_ip() {
  python3 - <<'PY'
import ipaddress
import json
import subprocess
import sys

try:
    result = subprocess.check_output(
        ["ip", "-j", "-4", "addr", "show", "dev", "eth0"], text=True
    )
except Exception:
    sys.exit()

try:
    data = json.loads(result)
except json.JSONDecodeError:
    sys.exit()

addr_info = []
if data:
    addr_info = data[0].get("addr_info", [])

preferred = None
fallback = None
for entry in addr_info:
    ip = entry.get("local")
    if not ip:
        continue
    if entry.get("dynamic"):
        preferred = ip
        break
    if fallback is None:
        fallback = ip

if preferred is None:
    private_block = ipaddress.ip_network("172.16.0.0/12")
    for entry in addr_info:
        ip = entry.get("local")
        if not ip:
            continue
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if ip_obj not in private_block:
            preferred = ip
            break

if preferred is None:
    preferred = fallback

if preferred:
    print(preferred)
PY
}

prefer_source_ip() {
  local preferred_ip="$1"
  if [[ -z "${preferred_ip}" ]]; then
    return
  fi

  local default_route gateway metric
  default_route=$(ip -o route show default dev eth0 | head -n1 || true)
  if [[ -z "${default_route}" ]]; then
    log_json "preferred_ip_error" reason="no_default_route" ip="${preferred_ip}"
    return
  fi

  gateway=$(awk '{for(i=1;i<=NF;i++){if($i=="via"){print $(i+1); exit}}}' <<<"${default_route}")
  if [[ -z "${gateway}" ]]; then
    log_json "preferred_ip_error" reason="no_gateway" ip="${preferred_ip}"
    return
  fi

  metric=$(awk '{for(i=1;i<=NF;i++){if($i=="metric"){print $(i+1); exit}}}' <<<"${default_route}")

  if [[ -n "${metric}" ]]; then
    if ip route replace default via "${gateway}" dev eth0 src "${preferred_ip}" metric "${metric}"; then
      log_json "preferred_ip" ip="${preferred_ip}" gateway="${gateway}" metric="${metric}"
    else
      log_json "preferred_ip_error" reason="route_replace_failed" ip="${preferred_ip}" gateway="${gateway}" metric="${metric}"
    fi
  else
    if ip route replace default via "${gateway}" dev eth0 src "${preferred_ip}"; then
      log_json "preferred_ip" ip="${preferred_ip}" gateway="${gateway}"
    else
      log_json "preferred_ip_error" reason="route_replace_failed" ip="${preferred_ip}" gateway="${gateway}"
    fi
  fi
}

read_dhcp_gateway() {
  python3 - <<'PY' || true
import json
import re
from pathlib import Path

leases_path = Path("/var/lib/dhcp/dhclient.leases")
if not leases_path.exists():
    raise SystemExit

pattern = re.compile(r"option routers (.+);")
gateway = None
try:
    for line in leases_path.read_text().splitlines():
        line = line.strip()
        match = pattern.match(line)
        if match:
            routers = [item.strip() for item in match.group(1).split(",") if item.strip()]
            if routers:
                gateway = routers[0]
except Exception:
    gateway = None

if gateway:
    print(gateway)
PY
}

correct_gateway() {
  local preferred_ip="${1:-}"
  local current_route gateway metric
  current_route=$(ip -o route show default dev eth0 | head -n1 || true)
  if [[ -z "${current_route}" ]]; then
    return
  fi

  gateway=$(awk '{for(i=1;i<=NF;i++){if($i=="via"){print $(i+1); exit}}}' <<<"${current_route}")
  metric=$(awk '{for(i=1;i<=NF;i++){if($i=="metric"){print $(i+1); exit}}}' <<<"${current_route}")

  if [[ -z "${gateway}" ]]; then
    return
  fi

  if python3 - "$gateway" <<'PY'
import ipaddress
import sys

gateway = sys.argv[1]
try:
    ip = ipaddress.ip_address(gateway)
except ValueError:
    raise SystemExit(1)

private_block = ipaddress.ip_network("172.16.0.0/12")
if ip in private_block:
    raise SystemExit(0)
raise SystemExit(1)
PY
  then
    local dhcp_gateway
    dhcp_gateway="$(read_dhcp_gateway || true)"
    if [[ -z "${dhcp_gateway}" || "${dhcp_gateway}" == "${gateway}" ]]; then
      return
    fi
    if [[ -n "${metric}" ]]; then
      if ip route replace default via "${dhcp_gateway}" dev eth0 src "${preferred_ip:-$dhcp_gateway}" metric "${metric}"; then
        log_json "gateway_corrected" gateway="${dhcp_gateway}" metric="${metric}"
      else
        log_json "gateway_correct_error" gateway="${dhcp_gateway}" metric="${metric}"
      fi
    else
      if ip route replace default via "${dhcp_gateway}" dev eth0 src "${preferred_ip:-$dhcp_gateway}"; then
        log_json "gateway_corrected" gateway="${dhcp_gateway}"
      else
        log_json "gateway_correct_error" gateway="${dhcp_gateway}"
      fi
    fi
  fi
}

: "${DEVICE_TYPE:=CAMERA_RTSP}"
: "${DEVICE_ID:=device-$(date +%s)}"
: "${HUB_IP:=127.0.0.1}"
: "${SERVER_IP:=${HUB_IP}}"
: "${ENABLE_DHCLIENT:=true}"
: "${ENABLE_BROADCAST:=true}"
: "${ENABLE_PAIRING:=true}"
: "${DISCOVERY_INTENSITY:=low}"
: "${DHCP_TEMPLATE_PATH:=/opt/iot/devices/configs/dhclient.jinja}"
: "${DHCP_TEMPLATE_DIR:=/opt/iot/devices/dhclient-templates}"
: "${HOSTS_TEMPLATE_PATH:=/opt/iot/devices/configs/hosts_map.template}"
: "${SAFE_MODE:=false}"

PERSONA_EXPORTS=$(python3 - <<'PY' "${DEVICE_TYPE}"
import json
import shlex
import sys
from pathlib import Path

import yaml

device_type = sys.argv[1]
profiles_path = Path("/opt/iot/devices/profiles.yaml")
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
emit("PERSONA_SCRIPT", persona.get("script", "scripts/heartbeat.py"))
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
emit("PERSONA_ROLE", persona.get("role", "client"))
PY
)

eval "${PERSONA_EXPORTS}"

if [[ -n "${VENDOR_OUI:-}" ]]; then
  PERSONA_VENDOR_OUI="${VENDOR_OUI}"
fi

if [[ -z "${ROLE:-}" ]]; then
  ROLE="${PERSONA_ROLE}"
fi
export ROLE

log_json "persona_selected" device_type="${DEVICE_TYPE}" display_name="${PERSONA_DISPLAY_NAME}" firmware="${FIRMWARE_VERSION}" role="${ROLE}"

MAC_ADDRESS="$(VENDOR_OUI="${PERSONA_VENDOR_OUI}" SAFE_MODE="${SAFE_MODE}" /opt/iot/devices/common/macgen.sh)"

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
    DHCP_IP="$(detect_preferred_ip)"
    if [[ -n "${DHCP_IP}" ]]; then
      PREFERRED_SOURCE_IP="${DHCP_IP}"
      prefer_source_ip "${DHCP_IP}"
      correct_gateway "${DHCP_IP}"
    else
      log_json "preferred_ip_error" reason="dhcp_ip_not_detected"
    fi
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
  if [[ -n "${PREFERRED_SOURCE_IP}" ]]; then
    echo "${PREFERRED_SOURCE_IP}"
    return
  fi
  local detected
  detected="$(detect_preferred_ip || true)"
  if [[ -n "${detected}" ]]; then
    PREFERRED_SOURCE_IP="${detected}"
    echo "${detected}"
  fi
}

DEVICE_IP="$(get_ip_address)"
if [[ -n "${DEVICE_IP}" ]]; then
  log_json "ip_acquired" ip="${DEVICE_IP}"
else
  log_json "ip_acquire_failed"
fi

register_once() {
  if [[ -z "${HUB_IP:-}" ]]; then
    log_json "hub_registration_skipped" reason="hub_ip_missing"
    return 1
  fi
  if [[ -z "${DEVICE_IP:-}" ]]; then
    log_json "hub_registration_skipped" reason="ip_missing"
    return 1
  fi
  python3 - <<'PY' "${HUB_IP}" "${DEVICE_ID}" "${DEVICE_TYPE}" "${ROLE}" "${DEVICE_IP}" "${PERSONA_PRIMARY_PROTOCOLS:-[]}" "${MAC_ADDRESS}" "${FIRMWARE_VERSION}" "${HUB_API_PORT:-7000}"
import json
import os
import sys
from urllib import request

hub_ip, device_id, device_type, role, ip_address, protocols_json, mac_address, firmware, hub_port = sys.argv[1:10]
try:
    protocols = json.loads(protocols_json) if protocols_json else []
except json.JSONDecodeError:
    protocols = []

payload = json.dumps(
    {
        "device_id": device_id,
        "device_type": device_type,
        "role": role,
        "ip_address": ip_address,
        "protocols": protocols,
        "mac": mac_address,
        "firmware": firmware,
    }
).encode()

url = f"http://{hub_ip}:{hub_port}/register"
req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
try:
    with request.urlopen(req, timeout=5) as resp:
        resp.read()
    print(json.dumps({"event": "hub_registered", "hub": hub_ip, "device_id": device_id}))
    sys.exit(0)
except Exception as exc:  # noqa: BLE001
    print(json.dumps({"event": "hub_register_error", "hub": hub_ip, "error": str(exc)}))
    sys.exit(1)
PY
}

register_with_hub_loop() {
  while true; do
    if register_once; then
      sleep 60
    else
      sleep 10
    fi
  done
}

if [[ "${ENABLE_BROADCAST}" == "true" ]]; then
  DISCOVERY_INTENSITY="${DISCOVERY_INTENSITY}" DEVICE_ID="${DEVICE_ID}" DEVICE_TYPE="${DEVICE_TYPE}" SERVER_IP="${SERVER_IP}" \
    /opt/iot/devices/common/chatter_generator.sh &
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

SCRIPT_PATH="/opt/iot/devices/scripts/${PERSONA_SCRIPT}"
if [[ ! -x "${SCRIPT_PATH}" ]]; then
  log_json "script_missing" path="${SCRIPT_PATH}"
  exit 1
fi

cleanup() {
  if [[ -n "${CHATTER_PID:-}" ]]; then
    kill "${CHATTER_PID}" 2>/dev/null || true
  fi
  if [[ -n "${HUB_REGISTER_PID:-}" ]]; then
    kill "${HUB_REGISTER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export DEVICE_TYPE DEVICE_ID SERVER_IP FIRMWARE_VERSION VULNERABILITY_PROFILE MALICIOUS_MODE PAYLOAD_TEMPLATE ROLE HUB_IP

hub_is_reachable() {
  if [[ -z "${HUB_IP:-}" ]]; then
    return 0
  fi
  if ping -c1 -W2 "${HUB_IP}" >/dev/null 2>&1; then
    return 0
  fi
  if python3 - "$HUB_IP" "${HUB_API_PORT:-7000}" <<'PY'
import socket
import sys

server = sys.argv[1]
ports = [int(sys.argv[2])]
for port in ports:
    try:
        with socket.create_connection((server, port), timeout=3):
            sys.exit(0)
    except OSError:
        continue
sys.exit(1)
PY
  then
    return 0
  fi
  return 1
}

wait_for_hub() {
  local delay=30
  while true; do
    if hub_is_reachable; then
      log_json "hub_reachable" hub_ip="${HUB_IP:-unknown}"
      break
    fi
    log_json "hub_unreachable" hub_ip="${HUB_IP:-unknown}" retry_in_sec="${delay}"
    sleep "${delay}"
  done
}

wait_for_hub

register_with_hub_loop &
HUB_REGISTER_PID=$!

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
