import asyncio
from abc import ABCMeta, abstractmethod
from typing import (Any, Callable, ClassVar, Dict, Set, Tuple, Type, TypeVar,
                    Union)

from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.status import Status

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

    status: Dict[Any, Status]

    def __init__(self) -> None:
        self.status = {}

    @abstractmethod
    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        pass

    def get_status(self, target: Any) -> Status:
        raise NotImplementedError

    @property
    @abstractmethod
    def launch_component(self) -> LaunchComponent:
        pass

    available_waiters: Dict[Any, asyncio.Event]

    async def wait_for_available(self, target: Any):
        status = self.get_status(target)
        if status.available:
            return
        try:
            await self.available_waiters.setdefault(target, asyncio.Event()).wait()
        finally:
            self.available_waiters.pop(target, None)

    def trig_available_waiters(self, target: Any):
        if target in self.available_waiters:
            self.available_waiters[target].set()
