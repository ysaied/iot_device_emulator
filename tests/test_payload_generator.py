from pathlib import Path

from devices.common.payload_generator import build_payload


def test_payload_generator_renders_placeholders(tmp_path):
    template = tmp_path / "template.json"
    template.write_text(
        '{"value": "{randint:1-5}", "firmware": "{firmware_version}", "device": "{device_id}"}'
    )
    payload = build_payload(
        template,
        {"device_id": "dev123", "firmware_version": "1.0.0", "server_ip": "1.2.3.4"},
    )
    assert payload["firmware"] == "1.0.0"
    assert payload["device"] == "dev123"
    assert 1 <= payload["value"] <= 5


def test_waveform_placeholder():
    template = Path("devices/common/payload_templates/ecg_mqtt.json")
    payload = build_payload(
        template,
        {"device_id": "ecg1", "firmware_version": "8.2.6", "server_ip": "1.1.1.1"},
    )
    assert "payload" in payload
    waveform = payload["payload"]["waveform"]
    assert waveform["type"] == "sinus"
    assert len(waveform["samples"]) == 20
