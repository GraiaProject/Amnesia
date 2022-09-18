from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from launart.service import ExportInterface, Service

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

    def io(self, id: K):
        return self.connections.get(id)


class AbstractServerService(Service):
    supported_interface_types = {AbstractRouter}
