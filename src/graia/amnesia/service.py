import asyncio
from abc import ABCMeta, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Set, Tuple, Type, TypeVar, Union

from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent

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

    available_waiters: Dict[Any, asyncio.Event]

    async def wait_for_available(self, target: Any):
        ...

    def trig_available_waiters(self, target: Any):
        if target in self.available_waiters:
            self.available_waiters[target].set()
