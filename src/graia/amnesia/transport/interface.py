import abc
import asyncio
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


class TransportInterface(Generic[T], metaclass=abc.ABCMeta):
    rider: "TransportRider"

    @abc.abstractmethod
    async def receive(self) -> T:
        raise NotImplementedError

    @abc.abstractmethod
    async def send(self, data: T) -> None:
        raise NotImplementedError

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
