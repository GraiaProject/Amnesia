from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.signature import TransportSignature

from .event import WebsocketCloseEvent as WebsocketCloseEvent
from .event import WebsocketConnectEvent as WebsocketConnectEvent
from .event import WebsocketReceivedEvent as WebsocketReceivedEvent
from .event import WebsocketReconnect as WebsocketReconnect
from .io import AbstractWebsocketIO as AbstractWebsocketIO
from .operator import WSConnectionAccept as WSConnectionAccept
from .operator import WSConnectionClose as WSConnectionClose


@dataclass
class WebsocketEndpoint(
    TransportSignature[None],
):
    path: str
    methods: Final[list[str]] = field(default_factory=lambda: ["GET"])
    method: Final[str] = "WS"

    def __hash__(self) -> int:
        return hash(self.path) + hash(id(self.methods))
