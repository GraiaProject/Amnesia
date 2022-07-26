from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import MutableMapping
from typing import Generic, TypeVar

from graia.amnesia.transport import Transport

K = TypeVar("K")
V = TypeVar("V")


class TransportRider(Generic[K, V], metaclass=ABCMeta):
    connections: MutableMapping[K, V]
    transports: list[Transport]

    @abstractmethod
    def io(self, id: K | None = None):
        raise NotImplementedError

    @abstractmethod
    def use(self, transport: Transport):
        raise NotImplementedError
