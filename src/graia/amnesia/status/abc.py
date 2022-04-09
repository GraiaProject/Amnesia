from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Optional, Set, TypeVar

if TYPE_CHECKING:
    from .manager import StatusManager

T = TypeVar("T")


class AbstractStatus(metaclass=ABCMeta):
    _manager: Optional["StatusManager"]

    @property
    def _internal_ready(self):
        return self._manager is not None

    def _set_manager(self, manager: "StatusManager"):
        self._manager = manager

    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def frame(self: T) -> T:
        ...

    @property
    @abstractmethod
    def required(self) -> Set[str]:
        ...

    @abstractmethod
    def update(self, *args, **kwargs):
        ...

    async def on_required_updated(self, id: str, past: Optional[T], current: Optional[T]):
        ...

    @property
    def available(self) -> bool:
        return True

    async def wait_for_update(self):
        if not self._internal_ready:
            raise RuntimeError(f"{self} is not ready")
        assert self._manager is not None
        ftr = self._manager._get_waiter(self)
        if not ftr:
            ftr = self._manager._ensure_waiter(self)
        await ftr

    async def wait_for_available(self):
        while not self.available:
            await self.wait_for_update()

    async def wait_for_unavailable(self):
        while self.available:
            await self.wait_for_update()
