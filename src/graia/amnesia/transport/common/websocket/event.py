from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from graia.amnesia.transport.common.status import ConnectionStatus
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.signature import TransportSignature

WebsocketConnectEvent: TransportSignature[
    Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]
] = TransportSignature()
WebsocketReceivedEvent: TransportSignature[
    Callable[[AbstractWebsocketIO, bytes | str], Coroutine[None, None, Any]]
] = TransportSignature()
WebsocketCloseEvent: TransportSignature[
    Callable[[AbstractWebsocketIO], Coroutine[None, None, Any]]
] = TransportSignature()
WebsocketReconnect: TransportSignature[Callable[[ConnectionStatus], Coroutine[None, None, bool]]] = TransportSignature()
