from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from launart import ExportInterface
from launart.service import Service


class AbstractAsgiService(Service):
    supported_interface_types = set()
    host: str
    port: int

    def get_interface(self, _):
        return

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        super().__init__()
        self.host = host
        self.port = port


class ASGIHandlerProvider(ExportInterface, metaclass=ABCMeta):
    @abstractmethod
    def get_asgi_handler(
        self,
    ) -> Callable[
        [
            type[MutableMapping[str, Any]],
            Awaitable[MutableMapping[str, Any]],
            Callable[[MutableMapping[str, Any]], Awaitable[None]],
        ],
        None,
    ]:
        ...


class ExternalASGIHandlerService(Service, ASGIHandlerProvider):
    supported_interface_types = {ASGIHandlerProvider}

    asgi: Callable[
        [
            type[MutableMapping[str, Any]],
            Awaitable[MutableMapping[str, Any]],
            Callable[[MutableMapping[str, Any]], Awaitable[None]],
        ],
        None,
    ]

    def __init__(
        self,
        asgi_handler: Callable[
            [
                type[MutableMapping[str, Any]],
                Awaitable[MutableMapping[str, Any]],
                Callable[[MutableMapping[str, Any]], Awaitable[None]],
            ],
            None,
        ],
    ) -> None:
        self.asgi = asgi_handler

    def get_interface(self, _):
        return self

    def get_asgi_handler(
        self,
    ) -> Callable[
        [
            type[MutableMapping[str, Any]],
            Awaitable[MutableMapping[str, Any]],
            Callable[[MutableMapping[str, Any]], Awaitable[None]],
        ],
        None,
    ]:
        return self.asgi
