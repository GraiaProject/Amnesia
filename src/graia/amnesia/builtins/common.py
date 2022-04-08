from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from graia.amnesia.launch.interface import ExportInterface

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, MutableMapping, Type


class ASGIHandlerProvider(ExportInterface, metaclass=ABCMeta):
    @abstractmethod
    def get_asgi_handler(
        self,
    ) -> """Callable[[
        Type[MutableMapping[str, Any]],
        Awaitable[MutableMapping[str, Any]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]]
    ], None]""":
        ...
