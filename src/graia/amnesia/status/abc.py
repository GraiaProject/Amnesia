from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Optional, Set, TypeVar

from typing_extensions import Self

if TYPE_CHECKING:
    from graia.amnesia.status.manager import StatusManager

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

    async def on_required_updated(self, id: str, past: T, current: T):
        ...

    @property
    def available(self) -> bool:
        return True

    async def wait_for_update(self) -> Self:
        ...

    async def wait_for_available(self):
        ...

    async def wait_for_unavailable(self):
        ...
