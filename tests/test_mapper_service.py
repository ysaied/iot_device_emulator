from scripts.mapper.mapper_service import build_mapping


def test_build_mapping_extracts_latest_entries():
    logs = {
        "logs": [
            {"event": "other", "mac": "00:00:00:00:00:01"},
            {
                "event": "device_mapping",
                "mac": "00:11:22:33:44:55",
                "device_type": "CAMERA_RTSP",
                "device_id": "cam01",
                "firmware": "2.1.4",
                "ip": "192.168.50.20",
                "timestamp": 123.0,
            },
            {
                "event": "device_mapping",
                "mac": "AA:BB:CC:DD:EE:FF",
                "device_type": "PLC_MODBUS",
                "device_id": "plc01",
                "firmware": "11.0.3",
                "ip": "192.168.50.30",
                "timestamp": 124.0,
            },
        ]
    }

    mapping = build_mapping(logs)
    assert len(mapping) == 2
    assert mapping["00:11:22:33:44:55"]["device_type"] == "CAMERA_RTSP"
    assert mapping["AA:BB:CC:DD:EE:FF"]["firmware_version"] == "11.0.3"
