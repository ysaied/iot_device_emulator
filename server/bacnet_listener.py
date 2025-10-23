#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json


class BacnetProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        try:
            payload = json.loads(data.decode())
        except json.JSONDecodeError:
            payload = {"raw": data.decode(errors="ignore")}
        print(json.dumps({"event": "bacnet_received", "payload": payload, "peer": addr[0]}), flush=True)

    def connection_made(self, transport) -> None:  # noqa: ANN001
        self.transport = transport
        print(json.dumps({"event": "bacnet_listen", "port": 47808}), flush=True)


async def main() -> None:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(BacnetProtocol, local_addr=("0.0.0.0", 47808))
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
