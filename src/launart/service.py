from __future__ import annotations

from abc import abstractmethod
from typing import Callable, ClassVar, Type, TypeVar

from graia.amnesia.utilles import PriorityType
from launart.component import Launchable
from launart.interface import ExportInterface

TInterface = TypeVar("TInterface", bound=ExportInterface)
TCallback = TypeVar("TCallback", bound=Callable)


class Service(Launchable):
    supported_interface_types: ClassVar[PriorityType[Type[ExportInterface]]]

    def __init__(self) -> None:
        ...

    @abstractmethod
    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        pass
