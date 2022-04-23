import asyncio
from abc import ABCMeta, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Set, Tuple, Type, TypeVar, Union

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface

TInterface = TypeVar("TInterface", bound=ExportInterface)
TCallback = TypeVar("TCallback", bound=Callable)


class Service(metaclass=ABCMeta):
    supported_interface_types: ClassVar[
        Union[
            Set[Type[ExportInterface]],
            Dict[Type[ExportInterface], Union[int, float]],
            Tuple[
                Union[
                    Set[Type[ExportInterface]],
                    Dict[Type[ExportInterface], Union[int, float]],
                ],
                ...,
            ],
        ]
    ]

    def __init__(self) -> None:
        ...

    @abstractmethod
    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        pass

    @property
    @abstractmethod
    def launch_component(self) -> LaunchComponent:
        pass
