import abc
import inspect
from typing import TYPE_CHECKING, Generic, Type, TypeVar, overload

from graia.amnesia.transport.signature import TransportSignature

if TYPE_CHECKING:
    from graia.amnesia.transport.rider import TransportRider


SPECIALLISTS = {"fields"}


class ExtraContent:
    @classmethod
    def fields(cls):
        return [
            name
            for name, field in inspect.getmembers(cls)
            if not name.startswith("_") and not callable(field) and name not in SPECIALLISTS
        ] + list(cls.__annotations__.keys())


E = TypeVar("E", bound=ExtraContent)
T = TypeVar("T")


class TransportIO(Generic[T], metaclass=abc.ABCMeta):
    rider: "TransportRider"

    @overload
    @abc.abstractmethod
    async def extra(self, signature: "Type[E]") -> E:
        ...

    @overload
    @abc.abstractmethod
    async def extra(self, signature: "Type[TransportSignature[T]] | TransportSignature[T]") -> T:
        ...

    @abc.abstractmethod
    async def extra(self, signature: ...):
        raise NotImplementedError

    def close(self):
        pass

    @property
    def closed(self):
        return False


class PacketIO(TransportIO[T]):
    @abc.abstractmethod
    async def receive(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    async def send(self, data: T):
        raise NotImplementedError


class StreamIO(TransportIO[T]):
    @abc.abstractmethod
    async def read(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    async def write(self, data: T):
        raise NotImplementedError


# 用于描述直接发过来一个然后让你 response 的, 像 HttpResponse 这种, 然后请求信息什么的全让你 extra.
# 然后结果就直接 handler 返回值, 主要用于 http server.
class ReadonlyIO(TransportIO[T]):
    @abc.abstractmethod
    async def read(self) -> T:
        raise NotImplementedError
