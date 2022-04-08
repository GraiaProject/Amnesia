from dataclasses import dataclass
from typing import Callable, Final

from graia.amnesia.transport.common import http
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.signature import TransportSignature


@dataclass
class endpoint(
    http.endpoint,
    TransportSignature[Callable[[AbstractWebsocketIO], None]],
):
    method: Final[str] = "WS"
