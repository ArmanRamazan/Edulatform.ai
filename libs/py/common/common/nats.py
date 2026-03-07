"""NATS JetStream client wrapper.

Factory: create_nats_client(url) → NATSClient

Lifecycle (call from service lifespan):
    client = create_nats_client(settings.nats_url)
    await client.connect()
    ...
    await client.close()

Publishing events:
    payload = json.dumps(event_dict).encode()
    await client.publish("platform.mastery.updated", payload)
"""

from __future__ import annotations

import nats
import nats.js


class NATSClient:
    """Thin wrapper around nats-py with auto-reconnect and JetStream support."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._nc: nats.NATS | None = None
        self.jetstream: nats.js.JetStreamContext | None = None

    async def connect(self) -> None:
        """Open connection to NATS server (idempotent)."""
        if self._nc is not None:
            return
        self._nc = await nats.connect(
            self.url,
            reconnect_time_wait=2,
            max_reconnect_attempts=-1,
        )
        self.jetstream = self._nc.jetstream()

    async def publish(self, subject: str, payload: bytes) -> None:
        """Publish *payload* to *subject* via JetStream.

        Raises RuntimeError if connect() has not been called.
        """
        if self.jetstream is None:
            raise RuntimeError("NATSClient is not connected — call connect() first")
        await self.jetstream.publish(subject, payload)

    async def close(self) -> None:
        """Drain and close the NATS connection (safe to call when not connected)."""
        if self._nc is None:
            return
        await self._nc.drain()
        self._nc = None
        self.jetstream = None


def create_nats_client(url: str) -> NATSClient:
    """Factory that returns a NATSClient for *url*."""
    return NATSClient(url)
