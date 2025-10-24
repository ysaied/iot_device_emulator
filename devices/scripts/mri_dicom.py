#!/usr/bin/env python3
from __future__ import annotations

import time

from pydicom.dataset import Dataset, FileMetaDataset
from pynetdicom import AE
from pynetdicom.sop_class import MRImageStorage, VerificationSOPClass

from pathlib import Path
import sys

PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from devices.scripts.common import DEVICE_ID, FIRMWARE_VERSION, SERVER_IP, json_log, jitter, malicious_ping


def build_dataset(sequence: int) -> Dataset:
    ds = Dataset()
    ds.PatientName = "MRI^PATIENT"
    ds.PatientID = DEVICE_ID
    ds.StudyDescription = "Synthetic MRI Study"
    ds.SeriesDescription = f"Sequence {sequence}"
    ds.Modality = "MR"
    base_uid = f"1.2.826.0.1.3680043.2.1125.{DEVICE_ID}"
    ds.StudyInstanceUID = base_uid
    ds.SeriesInstanceUID = f"{base_uid}.{sequence}"
    ds.SOPInstanceUID = f"{base_uid}.{sequence}.1"
    ds.SOPClassUID = MRImageStorage.uid
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = "1.2.840.10008.1.2.1"
    ds.file_meta.MediaStorageSOPClassUID = MRImageStorage.uid
    ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    ds.file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.8.498.2"
    ds.file_meta.ImplementationVersionName = FIRMWARE_VERSION
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    return ds


def send_sequence(ae: AE, sequence: int) -> None:
    assoc = ae.associate(SERVER_IP, 104)
    if assoc.is_established:
        status = assoc.send_c_store(build_dataset(sequence))
        json_log("dicom_sequence", sequence=sequence, status=str(status.Status))
        assoc.release()
    else:
        json_log("dicom_error", sequence=sequence, error="association_failed")


def main() -> None:
    ae = AE(ae_title=b"MRIDEVICE")
    ae.add_requested_context(VerificationSOPClass)
    ae.add_requested_context(MRImageStorage)
    sequence = 1
    while True:
        send_sequence(ae, sequence)
        malicious_ping("/mri")
        sequence += 1
        time.sleep(jitter(90))


if __name__ == "__main__":
    main()
