#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from pynetdicom import AE, evt
from pynetdicom.sop_class import (
    CTImageStorage,
    MRImageStorage,
    VerificationSOPClass,
)

DATA_DIR = Path("/data/dicom")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def handle_store(event):
    dataset = event.dataset
    dataset.file_meta = event.file_meta
    destination = DATA_DIR / f"{dataset.SOPInstanceUID}.dcm"
    dataset.save_as(destination, write_like_original=False)
    print(
        json.dumps(
            {
                "event": "dicom_store",
                "sop_class": str(dataset.SOPClassUID),
                "instance": dataset.SOPInstanceUID,
                "path": str(destination),
            }
        ),
        flush=True,
    )
    return 0x0000


handlers = [(evt.EVT_C_STORE, handle_store)]


def main() -> None:
    ae = AE(ae_title=b"IOTSERVER")
    ae.storage_sop_class_extended_negotiation = {}
    for sop in (CTImageStorage, MRImageStorage):
        ae.add_supported_context(sop)
    ae.add_supported_context(VerificationSOPClass)
    ae.start_server(("0.0.0.0", 104), block=True, evt_handlers=handlers)


if __name__ == "__main__":
    main()
