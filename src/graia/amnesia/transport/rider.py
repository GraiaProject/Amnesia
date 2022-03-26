import abc
from typing import List, Type, TypeVar, overload

from graia.amnesia.transport import Transport

T = TypeVar("T")


class TransportRider(metaclass=abc.ABCMeta):
    transports: List["Transport | Type[Transport]"]

    @abc.abstractmethod
    def ensure_transport(self, transport: "Transport | Type[Transport]") -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_transport(self, transport: "Transport | Type[Transport]") -> None:
        raise NotImplementedError
