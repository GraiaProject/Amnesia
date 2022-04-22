from dataclasses import dataclass
from typing import Callable, Final, Generic, Literal, TypeVar, Union

from graia.amnesia.transport.common import http
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature

from .event import WebsocketCloseEvent as WebsocketCloseEvent
from .event import WebsocketConnectEvent as WebsocketConnectEvent
from .event import WebsocketReceivedEvent as WebsocketReceivedEvent
from .io import AbstractWebsocketIO as AbstractWebsocketIO
from .operator import WSConnectionAccept as WSConnectionAccept
from .operator import WSConnectionClose as WSConnectionClose


@dataclass
class WebsocketEndpoint(
    http.HttpEndpoint,
    TransportSignature[None],
):
    method: Final[str] = "WS"

    def __hash__(self) -> int:
        return hash(self.path) + hash(id(self.methods))
