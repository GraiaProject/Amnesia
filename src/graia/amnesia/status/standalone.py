import asyncio
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Deque, Optional, Set, TypeVar

from typing_extensions import Self

from graia.amnesia.status.abc import AbstractStatus
from graia.amnesia.status.manager import TWaiterFtr

if TYPE_CHECKING:
    from .manager import StatusManager

T = TypeVar("T")


class AbstractStandaloneStatus(AbstractStatus, metaclass=ABCMeta):
    _manager = None

    def __init__(self) -> None:
        self._waiters: Deque[TWaiterFtr] = Deque()

    @property
    def _internal_ready(self):
        return True

    def _set_manager(self, manager: "StatusManager"):
        raise RuntimeError(f"{self} is a standalone status, it can not be set a manager.")

    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def frame(self: T) -> T:
        ...

    @property
    def required(self) -> Set[str]:
        return set()

    def notify(self, past: Self):
        for waiter in self._waiters:
            if not waiter.done():
                waiter.set_result((past, self.frame))

    @abstractmethod
    def update(self, *args, **kwargs):
        ...

    async def on_required_updated(self, id: str, past: Optional[T], current: Optional[T]):
        raise RuntimeError(f"{self} is a standalone status, it can not be updated by upstream.")

    @property
    def available(self) -> bool:
        return True

    async def wait_for_update(self):
        waiter = asyncio.Future()
        self._waiters.append(waiter)
        try:
            return await waiter
        finally:
            self._waiters.remove(waiter)

    async def wait_for_available(self):
        while not self.available:
            await self.wait_for_update()

    async def wait_for_unavailable(self):
        while self.available:
            await self.wait_for_update()
