from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from functools import reduce
from typing import Any, TypeVar

from launart.service import ExportInterface, Service
from launart.utilles import wait_fut

from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.io import AbstractServerRequestIO
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.rider import TransportRider

T = TypeVar("T", bound="AbstractServerService")
K = TypeVar("K")
V = TypeVar("V", bound="AbstractServerRequestIO | AbstractWebsocketIO")


class AbstractRouter(
    ExportInterface[T],
    TransportRider[K, V],
    metaclass=ABCMeta,
):
    @abstractmethod
    async def handle_http_request(self, handler: Callable[[AbstractServerRequestIO], Any], request: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def handle_websocket_request(self, request: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def use(self, transport: Transport):
        raise NotImplementedError

    async def trigger_callbacks(self, event, *args, **kwargs):
        callbacks = [i.get_callbacks(event) for i in self.transports if i.has_callback(event)]
        if callbacks:
            callbacks = reduce(lambda a, b: a + b, callbacks)
            await wait_fut([i(*args, **kwargs) for i in callbacks])

    def io(self, id: K):
        return self.connections.get(id)


class AbstractServerService(Service):
    id = "http.universal_server"
    supported_interface_types = {AbstractRouter}
