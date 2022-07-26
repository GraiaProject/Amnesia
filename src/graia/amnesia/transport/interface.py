from __future__ import annotations

from abc import ABCMeta, abstractmethod
from inspect import getmembers
from typing import Generic, TypeVar, overload

from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature

SPECIALLISTS = {"fields"}


class ExtraContent:
    @classmethod
    def fields(cls):
        return [
            name
            for name, field in getmembers(cls)
            if not name.startswith("_") and not callable(field) and name not in SPECIALLISTS
        ] + list(cls.__annotations__.keys())


E = TypeVar("E", bound=ExtraContent)
T = TypeVar("T")


class TransportIO(Generic[T], metaclass=ABCMeta):
    rider: TransportRider

    @overload
    @abstractmethod
    async def extra(self, signature: type[E]) -> E:
        ...

    @overload
    @abstractmethod
    async def extra(self, signature: type[TransportSignature[T]] | TransportSignature[T]) -> T:
        ...

    @abstractmethod
    async def extra(self, signature: ...):
        raise NotImplementedError

    def close(self):
        pass

    @property
    def closed(self):
        return False


class PacketIO(TransportIO[T]):
    @abstractmethod
    async def receive(self) -> T:
        raise NotImplementedError

    @abstractmethod
    async def send(self, data: T):
        raise NotImplementedError


class StreamIO(TransportIO[T]):
    @abstractmethod
    async def read(self) -> T:
        raise NotImplementedError

    @abstractmethod
    async def write(self, data: T):
        raise NotImplementedError


# 用于描述直接发过来一个然后让你 response 的, 像 HttpResponse 这种, 然后请求信息什么的全让你 extra.
# 然后结果就直接 handler 返回值, 主要用于 http server.
class ReadonlyIO(TransportIO[T]):
    @abstractmethod
    async def read(self) -> T:
        raise NotImplementedError
