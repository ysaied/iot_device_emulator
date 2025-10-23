#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

from pynetdicom import AE, evt
from pynetdicom.sop_class import CTImageStorage, MRImageStorage, Verification

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

DATA_DIR = Path("/data/dicom")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def handle_store(event):
    dataset = event.dataset
    dataset.file_meta = event.file_meta
    destination = DATA_DIR / f"{dataset.SOPInstanceUID}.dcm"
    try:
        dataset.save_as(destination, write_like_original=False)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to save DICOM object: %s", exc)
        return 0xC000
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
    for sop in (CTImageStorage, MRImageStorage):
        ae.add_supported_context(sop)
    ae.add_supported_context(Verification)
    while True:
        try:
            logging.info("Starting DICOM SCP on 0.0.0.0:11112")
            ae.start_server(("0.0.0.0", 11112), block=True, evt_handlers=handlers)
        except Exception as exc:  # noqa: BLE001
            logging.error("DICOM SCP encountered an error: %s", exc)
            time.sleep(5)
        else:
            break


if __name__ == "__main__":
    main()
