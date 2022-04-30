import asyncio
import contextlib
from functools import reduce
from typing import (
    TYPE_CHECKING,
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

from aiohttp import (
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    WSMsgType,
)
from loguru import logger
from typing_extensions import ParamSpec, Self

from graia.amnesia.launch.component import LaunchComponent
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.service import Service
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpResponse
from graia.amnesia.transport.common.http.io import AbstactClientRequestIO
from graia.amnesia.transport.common.status import ConnectionStatus
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


class AiohttpConnectionStatus(ConnectionStatus):
    def __init__(self) -> None:
        self.connected: bool = False
        self.succeed: bool = False
        self.drop: bool = False
        super().__init__("aiohttp.connection")

    def __repr__(self) -> str:
        return f"<ConnectionStatus {self.connected=:}, {self.succeed=:}, {self.drop=:}, {self._waiter=:}>"

    def update(
        self, connected: Optional[bool] = None, succeed: Optional[bool] = None, drop: Optional[bool] = None
    ) -> None:
        past = self.frame()
        if connected is not None:
            self.connected = connected
        if succeed is not None:
            self.succeed = succeed
        if drop is not None:
            self.drop = drop

        if self._waiter and not self._waiter.done():
            self._waiter.set_result((past, self))
        else:
            self._waiter = asyncio.Future()
            self._waiter.set_result((past, self))

    async def wait_for_drop(self) -> None:
        while not self.drop:
            await self.wait_for_update()


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

    async def cookies(self) -> Dict[str, str]:
        return {k: v.value for k, v in self.connection._response.cookies.items()}

    async def extra(self, signature):
        if signature is WebsocketClose:
            if not self.connection.closed:
                await self.connection.close()
        elif signature is HttpResponse:
            return HttpResponse(
                self.connection._response.status,
                dict(self.connection._response.request_info.headers),
                {k: v.value for k, v in self.connection._response.cookies.items()},
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
        self.status = AiohttpConnectionStatus()
        self.autoreceive: bool = False
        self.task = None
        self.connect_task = None
        self.interface = interface

    async def _connect(self):
        async with self.conn_func(**self.call_param) as resp:
            self.response = resp
            self.status.update(connected=True)
            await self.status.wait_for_drop()
            self.status.update(drop=False)
        self.status.update(connected=False)

    async def _start_conn(self) -> Self:
        if not self.status.available:
            self.response = None
            if self.connect_task is None:
                self.connect_task = asyncio.create_task(self._connect())
            await self.status.wait_for_available()
            self.status.update(succeed=True)
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
        if not self.status.connected:
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
                    self.status.update(drop=True)
                    await self.status.wait_for_unavailable()
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
                        tsk = asyncio.create_task(handler(self.status))
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
        if TYPE_CHECKING:
            session = session or ClientSession()
        self.session = session

    def get_interface(self, interface_type):
        if interface_type is AiohttpClientInterface:
            return AiohttpClientInterface(self)

    async def prepare(self, _):
        if not self.session:
            self.session = ClientSession(timeout=ClientTimeout(total=None))

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent(
            "http.universal_client", set(), prepare=self.prepare, cleanup=lambda _: self.session.close()
        )
