from typing import Any, Callable, Coroutine, Union

from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature

WebsocketConnectEvent = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
WebsocketReceivedEvent = TransportSignature[
    Callable[[AbstractWebsocketIO, Union[bytes, str]], Coroutine[None, None, Any]]
]()
WebsocketCloseEvent = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
WebsocketReconnect = TransportSignature[Callable[[TransportRider], Coroutine[None, None, bool]]]()
