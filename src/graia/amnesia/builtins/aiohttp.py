import asyncio
import contextlib
import weakref
from functools import partial, reduce
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

from aiohttp import ClientResponse, ClientSession, ClientWebSocketResponse, WSMsgType
from loguru import logger
from typing_extensions import ParamSpec, Self

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.service import Service
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpResponse
from graia.amnesia.transport.common.http.io import AbstactClientRequestIO
from graia.amnesia.transport.common.websocket.event import (
    WebsocketCloseEvent as WebsocketCloseEvent,
)
from graia.amnesia.transport.common.websocket.event import (
    WebsocketConnectEvent as WebsocketConnectEvent,
)
from graia.amnesia.transport.common.websocket.event import (
    WebsocketReceivedEvent as WebsocketReceivedEvent,
)
from graia.amnesia.transport.common.websocket.event import (
    WebsocketReconnect as WebsocketReconnect,
)
from graia.amnesia.transport.common.websocket.io import AbstractWebsocketIO
from graia.amnesia.transport.common.websocket.operator import (
    WSConnectionAccept as WebsocketAccept,
)
from graia.amnesia.transport.common.websocket.operator import (
    WSConnectionClose as WebsocketClose,
)
from graia.amnesia.transport.exceptions import ConnectionClosed
from graia.amnesia.transport.interface import TransportIO
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature


class ClientRequestIO(AbstactClientRequestIO):
    response: ClientResponse

    def __init__(self, response: ClientResponse) -> None:
        self.response = response

    async def read(self) -> bytes:
        return await self.response.read()

    async def extra(self, signature):
        if signature is HttpResponse:
            return HttpResponse(
                self.response.status,
                dict(self.response.headers),
                {k: str(v) for k, v in self.response.cookies.items()},
                self.response.url,
            )


class ClientWebsocketIO(AbstractWebsocketIO):
    connection: ClientWebSocketResponse

    def __init__(self, connection: ClientWebSocketResponse) -> None:
        self.connection = connection

    async def extra(self, signature):
        if signature is WebsocketClose:
            if not self.connection.closed:
                await self.connection.close()
        elif signature is HttpResponse:
            return HttpResponse(
                self.connection._response.status,
                dict(self.connection._response.request_info.headers),
                dict(self.connection._response.request_info.url.query),
                self.connection._response.request_info.url,
            )

    async def receive(self) -> Union[bytes, str]:
        msg = await self.connection.receive()
        if msg.type in {WSMsgType.TEXT, WSMsgType.BINARY}:
            return msg.data
        # 错误处理
        if msg.type in {WSMsgType.CLOSE, WSMsgType.CLOSED}:
            raise ConnectionClosed("websocket closed")
        elif msg.type == WSMsgType.ERROR:
            raise msg.data
        else:
            raise TypeError(f"unexpected websocket message type: {msg.type}")

    async def send(self, data: "str | bytes | Any"):
        if isinstance(data, str):
            await self.connection.send_str(data)
        elif isinstance(data, bytes):
            await self.connection.send_bytes(data)
        else:
            await self.connection.send_json(data)

    @property
    def closed(self):
        return self.connection.closed

    async def wait_for_ready(self):
        if self.closed:
            raise ConnectionClosed("websocket closed")


T = TypeVar("T", ClientResponse, ClientWebSocketResponse)

P = ParamSpec("P")


class ClientConnectionRider(TransportRider[str, T], Generic[T]):
    def __init__(
        self,
        interface: "AiohttpClientInterface",
        conn_func: Callable[..., AsyncContextManager[T]],
        call_param: Dict[str, Any],
    ) -> None:
        self.transports: List[Transport] = []
        self.connections = {}
        self.response: Optional[T] = None
        self.conn_func = conn_func
        self.call_param = call_param
        self.keep_connection: bool = True
        self._stat_updater: Optional[asyncio.Event] = None
        self.connected: bool = False
        self.connected_sentinel: Optional[asyncio.Future] = None
        self.autoreceive: bool = False
        self.task = None
        self.connect_task = None
        self.interface = interface

    async def _update_conn(self):
        if not self._stat_updater:
            self._stat_updater = asyncio.Event()
        self._stat_updater.set()
        self._stat_updater.clear()

    async def _connect(self):
        async with self.conn_func(**self.call_param) as resp:
            self.response = resp
            self.connected = True
            await self._update_conn()
            assert self._stat_updater
            while self.keep_connection:
                await self._stat_updater.wait()
            self.connected = False
            await self._update_conn()

    async def _start_conn(self) -> Self:
        self.response = None
        await self._update_conn()  # init self._stat_updater
        assert self._stat_updater
        if self.connect_task is None:
            self.connect_task = asyncio.create_task(self._connect())
        while not self.connected:
            await self._stat_updater.wait()
        return self

    def __await__(self):
        return self._start_conn().__await__()

    @overload
    def io(self: "ClientConnectionRider[ClientResponse]") -> ClientRequestIO:
        ...

    @overload
    def io(self: "ClientConnectionRider[ClientWebSocketResponse]") -> ClientWebsocketIO:
        ...

    def io(self, id=None) -> ...:
        if id:
            raise TypeError("this rider has just one connection")
        if self.autoreceive:
            raise TypeError("this rider has been taken over by auto receive, use .use(transport) instead.")
        if not self.connected:
            raise RuntimeError("the connection is not ready, please await the instance to ensure connection")
        assert self.response
        if isinstance(self.response, ClientWebSocketResponse):
            return ClientWebsocketIO(self.response)
        elif isinstance(self.response, ClientResponse):
            return ClientRequestIO(self.response)
        else:
            raise TypeError("this response is not a ClientResponse or ClientWebSocketResponse")

    async def trigger_callbacks(self, event, *args, **kwargs):
        callbacks = [i.get_callbacks(event) for i in self.transports if i.has_callback(event)]
        if callbacks:
            callbacks = reduce(lambda a, b: a + b, callbacks)
            await asyncio.wait([i(*args, **kwargs) for i in callbacks])

    async def connection_manage(self):
        __original_transports: List[Transport] = self.transports[:]

        with contextlib.suppress(Exception):
            while self.transports:
                try:
                    await self._start_conn()
                    assert isinstance(
                        self.response, ClientWebSocketResponse
                    ), f"{self.response} is not a ClientWebSocketResponse"
                    io = ClientWebsocketIO(self.response)
                    await self.trigger_callbacks(WebsocketConnectEvent, io)
                    try:
                        async for data in io.packets():
                            await self.trigger_callbacks(WebsocketReceivedEvent, io, data)
                    except ConnectionClosed:
                        pass
                    await self.trigger_callbacks(WebsocketCloseEvent, io)
                    if not io.closed:
                        await io.close()
                    self.keep_connection = False
                    assert self._stat_updater
                    await self._update_conn()
                    while self.connected:
                        await self._stat_updater.wait()  # drop connection
                    self.keep_connection = True
                    self.connect_task = None
                except Exception as e:
                    logger.exception(e)
                # scan transports
                continuing_transports: List[Transport] = self.transports[:]
                self.transports = []
                reconnect_handle_tasks = []
                for t in continuing_transports:
                    handler = t.get_handler(WebsocketReconnect)
                    if handler:
                        tsk = asyncio.create_task(handler(self))
                        tsk.add_done_callback(lambda tsk: self.transports.append(t) if tsk.result() is True else None)
                        reconnect_handle_tasks.append(tsk)
                await asyncio.wait(reconnect_handle_tasks, return_when=asyncio.ALL_COMPLETED)
        self.transports = __original_transports

    def use(self, transport: Transport):
        self.autoreceive = True
        self.transports.append(transport)
        if not self.task:
            self.task = asyncio.create_task(self.connection_manage())
        return self.task


class AiohttpClientInterface(ExportInterface["AiohttpService"]):
    service: "AiohttpService"

    def __init__(self, service: "AiohttpService") -> None:
        self.service = service

    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> ClientConnectionRider[ClientResponse]:
        call_param: Dict[str, Any] = {
            "method": method,
            "url": url,
            "params": params,
            "data": data,
            "headers": headers,
            "cookies": cookies,
            "timeout": timeout,
            **kwargs,
        }
        return ClientConnectionRider(self, self.service.session.request, call_param)

    def websocket(self, url: str, **kwargs) -> ClientConnectionRider[ClientWebSocketResponse]:
        call_param: Dict[str, Any] = {"url": url, **kwargs}
        return ClientConnectionRider(self, self.service.session.ws_connect, call_param)


class AiohttpService(Service):
    session: ClientSession
    supported_interface_types = {AiohttpClientInterface}

    def __init__(self, session: Optional[ClientSession] = None) -> None:
        self.session = session or ClientSession()

    def get_interface(self, interface_type):
        if interface_type is AiohttpClientInterface:
            return AiohttpClientInterface(self)

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent("http.universal_client", set(), cleanup=lambda _: self.session.close())
