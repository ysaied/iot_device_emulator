#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json


class CoapProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr) -> None:  # noqa: ANN001
        try:
            payload = json.loads(data.decode())
        except json.JSONDecodeError:
            payload = {"raw": data.decode(errors="ignore")}
        print(json.dumps({"event": "coap_received", "payload": payload, "peer": addr[0]}), flush=True)
        response = json.dumps({"status": "ok"}).encode()
        self.transport.sendto(response, addr)

    def connection_made(self, transport) -> None:  # noqa: ANN001
        self.transport = transport
        print(json.dumps({"event": "coap_listen", "port": 5683}), flush=True)


async def main() -> None:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(CoapProtocol, local_addr=("0.0.0.0", 5683))
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
