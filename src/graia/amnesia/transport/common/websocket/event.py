from typing import Any, Callable, Coroutine, Union

from graia.amnesia.transport.common.status import ConnectionStatus
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.signature import TransportSignature

WebsocketConnectEvent = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
WebsocketReceivedEvent = TransportSignature[
    Callable[[AbstractWebsocketIO, Union[bytes, str]], Coroutine[None, None, Any]]
]()
WebsocketCloseEvent = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
WebsocketReconnect = TransportSignature[Callable[[ConnectionStatus], Coroutine[None, None, bool]]]()
