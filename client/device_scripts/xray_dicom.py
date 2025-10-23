#!/usr/bin/env python3
from __future__ import annotations

import time

from pydicom.dataset import Dataset, FileMetaDataset
from pynetdicom import AE
from pynetdicom.sop_class import CTImageStorage, VerificationSOPClass

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from client.device_scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


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


def send_c_store(ae: AE) -> None:
    assoc = ae.associate(SERVER_IP, 104)
    if assoc.is_established:
        status = assoc.send_c_store(build_dataset())
        json_log("dicom_c_store", status=str(status.Status))
        assoc.release()
    else:
        json_log("dicom_error", error="association_failed")


def main() -> None:
    ae = AE(ae_title=b"XRAYDEVICE")
    ae.add_requested_context(VerificationSOPClass)
    ae.add_requested_context(CTImageStorage)
    while True:
        send_c_store(ae)
        malicious_ping("/dicom")
        time.sleep(jitter(60))


if __name__ == "__main__":
    main()
