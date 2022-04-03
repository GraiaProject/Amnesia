import abc
from typing import Dict, Generic, List, Optional, Type, TypeVar, overload

from graia.amnesia.transport import Transport

K = TypeVar("K")
V = TypeVar("V")


class TransportRider(Generic[K, V], metaclass=abc.ABCMeta):
    connections: Dict[K, V]
    transports: List[Transport]

    @abc.abstractmethod
    def io(self, id: Optional[K] = None):
        raise NotImplementedError

    @abc.abstractmethod
    def use(self, transport: Transport):
        raise NotImplementedError
