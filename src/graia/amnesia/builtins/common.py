from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, MutableMapping, Type

    from graia.amnesia.interface import ExportInterface


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
