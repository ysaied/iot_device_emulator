#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

from pydicom.dataset import Dataset, FileMetaDataset
from pynetdicom import AE, evt
from pynetdicom.sop_class import CTImageStorage, Verification

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import (  # noqa: E402
    DEVICE_ID,
    FIRMWARE_VERSION,
    HUB_IP,
    SERVER_IP,
    is_client,
    is_server,
    json_log,
    jitter,
    malicious_ping,
)

DICOM_PORT = int(os.environ.get("DICOM_PORT", "11112"))


def build_dataset() -> Dataset:
    ds = Dataset()
    ds.PatientName = "XRAY^PATIENT"
    ds.PatientID = f"{DEVICE_ID}"
    ds.StudyDescription = "Synthetic X-Ray Study"
    ds.SeriesDescription = "Metadata only"
    ds.Modality = "DX"
    ds.StudyInstanceUID = f"1.2.826.0.1.3680043.2.1125.{DEVICE_ID}"
    ds.SeriesInstanceUID = f"1.2.826.0.1.3680043.2.1125.{DEVICE_ID}.1"
    ds.SOPInstanceUID = f"1.2.826.0.1.3680043.2.1125.{DEVICE_ID}.1.1"
    ds.SOPClassUID = CTImageStorage.uid
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds.file_meta.MediaStorageSOPClassUID = CTImageStorage.uid
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.8.498.1"
    ds.file_meta.ImplementationVersionName = FIRMWARE_VERSION
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    return ds


def run_client() -> None:
    target = SERVER_IP or HUB_IP
    ae = AE(ae_title=b"XRAYDEVICE")
    ae.add_requested_context(Verification)
    ae.add_requested_context(CTImageStorage)
    while True:
        assoc = ae.associate(target, DICOM_PORT)
        if assoc.is_established:
            status = assoc.send_c_store(build_dataset())
            json_log("dicom_c_store", status=str(status.Status))
            assoc.release()
        else:
            json_log("dicom_error", error="association_failed")
        malicious_ping("/dicom")
        time.sleep(jitter(60))


def run_server() -> None:
    ae = AE(ae_title=b"XRAYSERVER")
    ae.add_supported_context(CTImageStorage)
    ae.add_supported_context(Verification)

    DATA_DIR = Path("/data/dicom")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def handle_store(event):
        dataset = event.dataset
        dataset.file_meta = event.file_meta
        destination = DATA_DIR / f"{dataset.SOPInstanceUID}.dcm"
        try:
            dataset.save_as(destination, write_like_original=False)
            json_log("dicom_store", sop_class=str(dataset.SOPClassUID), path=str(destination))
        except Exception as exc:  # noqa: BLE001
            json_log("dicom_store_error", error=str(exc))
            return 0xC000
        return 0x0000

    handlers = [(evt.EVT_C_STORE, handle_store)]
    while True:
        try:
            json_log("dicom_server_start", port=DICOM_PORT)
            ae.start_server(("0.0.0.0", DICOM_PORT), block=True, evt_handlers=handlers)
        except Exception as exc:  # noqa: BLE001
            json_log("dicom_server_error", error=str(exc))
            time.sleep(5)
        else:
            break


def main() -> None:
    threads: list[threading.Thread] = []
    if is_server():
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        threads.append(server_thread)
    if is_client():
        run_client()
    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
