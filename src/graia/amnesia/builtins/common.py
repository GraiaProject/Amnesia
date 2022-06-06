from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from launart import ExportInterface
from launart.service import Service

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


class ExternalASGIHandlerService(Service, ASGIHandlerProvider):
    supported_interface_types = {ASGIHandlerProvider}

    asgi: """Callable[[
        Type[MutableMapping[str, Any]],
        Awaitable[MutableMapping[str, Any]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]]
    ], None]"""

    def __init__(
        self,
        asgi_handler: """Callable[[
        Type[MutableMapping[str, Any]],
        Awaitable[MutableMapping[str, Any]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]]
    ], None]""",
    ) -> None:
        self.asgi = asgi_handler

    def get_interface(self, _):
        return self

    def get_asgi_handler(
        self,
    ) -> """Callable[[
        Type[MutableMapping[str, Any]],
        Awaitable[MutableMapping[str, Any]],
        Callable[[MutableMapping[str, Any]], Awaitable[None]]
    ], None]""":
        return self.asgi
