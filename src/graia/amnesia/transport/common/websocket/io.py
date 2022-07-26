from __future__ import annotations

from abc import abstractmethod
from typing import Any, TypeVar, overload

from graia.amnesia.transport.common.websocket.operator import (
    WSConnectionAccept,
    WSConnectionClose,
)
from graia.amnesia.transport.exceptions import ConnectionClosed
from graia.amnesia.transport.interface import ExtraContent, PacketIO
from graia.amnesia.transport.signature import TransportSignature

T = TypeVar("T")
E = TypeVar("E", bound=ExtraContent)


class AbstractWebsocketIO(PacketIO["str | bytes"]):
    @abstractmethod
    async def receive(self) -> str | bytes:
        raise NotImplementedError

    @overload
    @abstractmethod
    async def send(self, data: bytes):
        ...

    @overload
    @abstractmethod
    async def send(self, data: str):
        ...

    @overload
    @abstractmethod
    async def send(self, data: Any):
        ...

    @abstractmethod
    async def send(self, data: ...):
        raise NotImplementedError

    @overload
    @abstractmethod
    async def extra(self, signature: type[TransportSignature[T]] | TransportSignature[T]) -> T:
        ...

    @overload
    @abstractmethod
    async def extra(self, signature: type[E]) -> E:
        ...

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

    @abstractmethod
    async def wait_for_ready(self):
        pass

    async def accept(self):
        await self.extra(WSConnectionAccept)

    async def close(self):
        if not self.closed:
            await self.extra(WSConnectionClose)

    async def packets(self):
        try:
            while not self.closed:
                yield await self.receive()
        except ConnectionClosed:
            raise
        except Exception:
            pass
