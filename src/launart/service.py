from __future__ import annotations

from abc import abstractmethod
from typing import Callable, ClassVar, Generic, Type, TypeVar

from graia.amnesia.utilles import PriorityType
from launart.component import Launchable

TService = TypeVar("TService", bound="Service")


class ExportInterface(Generic[TService]):
    service: TService


TInterface = TypeVar("TInterface", bound=ExportInterface)
TCallback = TypeVar("TCallback", bound=Callable)


class Service(Launchable):
    supported_interface_types: ClassVar[PriorityType[Type[ExportInterface]]]

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        pass
