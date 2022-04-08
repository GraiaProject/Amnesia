from typing import Any, Callable, Coroutine, Union

from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.signature import TransportSignature

connect = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
receive = TransportSignature[Callable[[AbstractWebsocketIO, Union[bytes, str]], Coroutine[None, None, Any]]]()
close = TransportSignature[Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]]()
