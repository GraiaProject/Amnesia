from abc import abstractmethod
from typing import Any, Union, overload

from graia.amnesia.transport.common.websocket.operator import (
    WSConnectionAccept,
    WSConnectionClose,
)
from graia.amnesia.transport.exceptions import ConnectionClosed
from graia.amnesia.transport.interface import PacketIO


class AbstractWebsocketIO(PacketIO[Union[str, bytes]]):
    @abstractmethod
    async def receive(self) -> Union[str, bytes]:
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

    @abstractmethod
    async def extra(self, signature: Any):
        raise NotImplementedError

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
