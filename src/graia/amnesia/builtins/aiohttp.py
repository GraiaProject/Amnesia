from __future__ import annotations

import asyncio
import contextlib
import pathlib
from functools import partial, reduce
from io import IOBase
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
from weakref import WeakValueDictionary

import aiohttp
from aiohttp import (
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    WSMsgType,
    web,
)
from launart import ExportInterface, Service
from launart.manager import Launart
from launart.utilles import wait_fut
from loguru import logger
from statv import Stats
from typing_extensions import ParamSpec, Self

from graia.amnesia.json import Json, TJson
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import (
    AbstractClientInterface,
    AbstractServerRequestIO,
)
from graia.amnesia.transport.common.http import HttpEndpoint as HttpEndpoint
from graia.amnesia.transport.common.http.extra import HttpRequest, HttpResponse
from graia.amnesia.transport.common.http.io import AbstractClientRequestIO
from graia.amnesia.transport.common.status import ConnectionStatus
from graia.amnesia.transport.common.websocket import AbstractWebsocketIO
from graia.amnesia.transport.common.websocket import (
    WebsocketEndpoint as WebsocketEndpoint,
)
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
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.signature import TransportSignature
from graia.amnesia.utilles import random_id


class AiohttpConnectionStatus(ConnectionStatus):
    drop = Stats[bool]("drop", default=False)

    def __init__(self) -> None:
        super().__init__()

    def __repr__(self) -> str:
        return f"<ConnectionStatus {self.connected=:}, {self.succeed=:}, {self.drop=:}, {self._waiters=:}>"

    async def wait_for_drop(self) -> None:
        while not self.drop:
            await self.wait_for_update()


class ClientRequestIO(AbstractClientRequestIO):
    rider: ClientConnectionRider[ClientResponse]
    response: ClientResponse

    def __init__(self, rider: ClientConnectionRider) -> None:
        assert rider.response
        self.rider = rider
        self.response = rider.response

    async def read(self) -> bytes:
        data = await self.response.read()
        if self.rider.status.connected and not self.rider.status.drop:
            self.close()
        return data

    async def extra(self, signature):
        if signature is HttpResponse:
            return HttpResponse(
                self.response.status,
                dict(self.response.headers),
                {k: str(v) for k, v in self.response.cookies.items()},
                self.response.url,
            )

    def close(self):
        self.rider.status.drop = True


class ClientWebsocketIO(AbstractWebsocketIO):
    rider: ClientConnectionRider[ClientWebSocketResponse]
    connection: ClientWebSocketResponse

    def __init__(self, rider: ClientConnectionRider) -> None:
        assert rider.response
        self.rider = rider
        self.connection = rider.response

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
        try:
            if isinstance(data, str):
                await self.connection.send_str(data)
            elif isinstance(data, bytes):
                await self.connection.send_bytes(data)
            else:
                await self.connection.send_json(data)
        except ConnectionError as e:
            raise ConnectionClosed(e.__class__.__qualname__, *e.args) from None

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
        interface: AiohttpClientInterface,
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
            self.status.connected = True
            await self.status.wait_for_drop()
            self.status.drop = False
        self.status.connected = False

    async def _start_conn(self) -> Self:
        if not self.status.available:
            self.response = None
            if self.connect_task is None:
                self.connect_task = asyncio.create_task(self._connect())
            await wait_fut((self.status.wait_for_available(), self.connect_task), return_when=asyncio.FIRST_COMPLETED)
            if self.connect_task.done():
                exc = self.connect_task.exception()
                self.connect_task = None
                if exc:
                    raise exc
            self.status.succeed = True
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
            return ClientWebsocketIO(self)
        elif isinstance(self.response, ClientResponse):
            return ClientRequestIO(self)
        else:
            raise TypeError("this response is not a ClientResponse or ClientWebSocketResponse")

    async def trigger_callbacks(self, event: TransportSignature[Callable[P, Any]], *args: P.args, **kwargs: P.kwargs):
        tasks: List[asyncio.Task] = []
        for i in self.transports:
            if i.has_callback(event):
                tasks.extend(asyncio.create_task(f(*args, **kwargs)) for f in i.get_callbacks(event))
        for task in tasks:
            await task

    async def connection_manage(self):
        __original_transports: List[Transport] = self.transports[:]

        with contextlib.suppress(Exception):
            while self.transports and self.interface.service.status.stage != "finished":
                try:
                    await self._start_conn()
                    assert isinstance(
                        self.response, ClientWebSocketResponse
                    ), f"{self.response} is not a ClientWebSocketResponse"
                    io = ClientWebsocketIO(self)
                    await self.trigger_callbacks(WebsocketConnectEvent, io)
                    with contextlib.suppress(ConnectionClosed):
                        async for data in io.packets():
                            await self.trigger_callbacks(WebsocketReceivedEvent, io, data)
                    await self.trigger_callbacks(WebsocketCloseEvent, io)
                    if not io.closed:
                        await io.close()
                    self.status.drop = True
                    await self.status.wait_for_unavailable()
                    self.connect_task = None
                except aiohttp.ClientConnectionError as e:
                    logger.warning(repr(e))
                except Exception as e:
                    logger.exception(e)
                # scan transports
                if self.interface.service.status == "cleanup":
                    continue
                continuing_transports: List[Transport] = self.transports[:]
                self.transports = []
                reconnect_handle_tasks = []
                for t in continuing_transports:
                    if t.has_handler(WebsocketReconnect):
                        handler = t.get_handler(WebsocketReconnect)
                        tsk = asyncio.create_task(handler(self.status))
                        tsk.add_done_callback(lambda tsk: self.transports.append(t) if tsk.result() is True else None)
                        reconnect_handle_tasks.append(tsk)
                await wait_fut(reconnect_handle_tasks)
        self.transports = __original_transports

    def use(self, transport: Transport):
        self.autoreceive = True
        self.transports.append(transport)
        if not self.task:
            self.task = asyncio.create_task(self.connection_manage())
        return self.task


class AiohttpClientInterface(AbstractClientInterface["AiohttpService"]):
    service: AiohttpService

    def __init__(self, service: AiohttpService) -> None:
        self.service = service

    def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: Optional[float] = None,
        *,
        json: Optional[TJson] = None,
        **kwargs: Any,
    ) -> ClientConnectionRider[ClientResponse]:
        if json:
            data = Json.serialize(json)
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
    id = "http.universal_client"
    session: ClientSession
    supported_interface_types = {AiohttpClientInterface}

    def __init__(self, session: Optional[ClientSession] = None) -> None:
        if TYPE_CHECKING:
            session = session or ClientSession()
        self.session = session
        super().__init__()

    def get_interface(self, interface_type):
        if interface_type is AiohttpClientInterface:
            return AiohttpClientInterface(self)

    @property
    def stages(self):
        return {"preparing", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, mgr: Launart):
        async with self.stage("preparing"):
            if not self.session:
                self.session = ClientSession(timeout=ClientTimeout(total=None))
        async with self.stage("cleanup"):
            await self.session.close()


class AiohttpServerRequestIO(AbstractServerRequestIO):
    request: web.Request

    def __init__(self, request: web.Request) -> None:
        self.request = request

    async def read(self) -> bytes:
        return await self.request.content.read()

    async def extra(self, signature):
        if signature is HttpRequest:
            return HttpRequest(
                dict(self.request.headers),
                dict(self.request.cookies),
                dict(self.request.query),
                self.request.url,
                self.request.host,
                self.request.method,
                self.request.remote or ".0.0.0",
                0,
            )


class AiohttpServerWebsocketIO(AbstractWebsocketIO):
    websocket: web.WebSocketResponse
    request: web.Request
    ready: asyncio.Event

    def __init__(self, request: web.Request) -> None:
        self.websocket = web.WebSocketResponse(autoping=True)
        self.request = request
        self.ready = asyncio.Event()

    async def receive(self) -> Union[str, bytes]:
        try:
            received = await self.websocket.receive()
        except asyncio.CancelledError as e:
            raise ConnectionClosed("Cancelled") from e
        if received.type in (web.WSMsgType.BINARY, web.WSMsgType.TEXT):
            return received.data
        elif received.type in (web.WSMsgType.CLOSE, web.WSMsgType.CLOSING, web.WSMsgType.CLOSED):
            self.ready.clear()
            raise ConnectionClosed("Connection closed")
        elif received.type is web.WSMsgType.ERROR:
            exc = self.websocket.exception()
            raise ConnectionClosed("Websocket Error") from exc
        raise TypeError(f"Unknown type of received message {received}")

    async def send(self, data: Union[str, bytes, Any]):
        if isinstance(data, str):
            await self.websocket.send_str(data)
        elif isinstance(data, bytes):
            await self.websocket.send_bytes(data)
        else:
            await self.websocket.send_json(data)

    async def extra(self, signature):
        if signature is HttpRequest:
            return HttpRequest(
                dict(self.request.headers),
                dict(self.request.cookies),
                dict(self.request.query),
                self.request.url,
                self.request.host,
                self.request.method,
                self.request.remote or ".0.0.0",
                0,
            )
        elif signature is WebsocketAccept:
            await self.websocket.prepare(self.request)
            self.ready.set()
        elif signature is WebsocketClose:
            await self.websocket.close()

    async def wait_for_ready(self):
        return await self.ready.wait()

    async def accept(self):
        return await super().accept()

    async def headers(self) -> Dict[str, str]:
        return dict(self.websocket.headers)

    async def cookies(self) -> Dict[str, str]:
        return dict(self.request.cookies)

    async def close(self):
        await self.websocket.close()

    @property
    def closed(self):
        return self.websocket.closed


class AiohttpRouter(
    ExportInterface["AiohttpServerService"],
    TransportRider[str, Union[AiohttpServerRequestIO, AiohttpServerWebsocketIO]],
):
    def __init__(self, wsgi: web.Application) -> None:
        self.connections = WeakValueDictionary()
        self.transports = []
        self.wsgi = wsgi

    async def handle_http_request(self, handler: Callable[[AiohttpServerRequestIO], Any], request: web.Request):
        req_io = AiohttpServerRequestIO(request)
        conn_id = random_id()
        self.connections[conn_id] = req_io
        try:
            handler_resp = await handler(req_io)
        finally:
            del self.connections[conn_id]
        if not isinstance(handler_resp, tuple):
            body = handler_resp
            resp_info = {}
        else:
            body = handler_resp[0]
            resp_info = reduce(lambda x, y: dict(x, **y), handler_resp[1:], {})
        status: int = resp_info.get("status", 200)
        if isinstance(body, (str, bytes, IOBase)):
            response = web.Response(body=body, status=status)
        elif isinstance(body, (dict, list)):
            response = web.json_response(body, status=status, headers=resp_info.get("headers"))
        elif isinstance(body, pathlib.Path):
            response = web.Response(body=body.open("rb"), status=status)
        elif isinstance(body, web.Response):
            response = body
        else:
            raise ValueError(f"unsupported response type {type(body)}")

        if "cookies" in resp_info:
            expire = resp_info.get("cookie_expires")
            for key, value in resp_info["cookies"].items():
                response.set_cookie(key, value, expires=expire)

        return response

    async def handle_websocket_request(self, request: web.Request) -> web.WebSocketResponse:
        websocket_io = AiohttpServerWebsocketIO(request)
        conn_id = random_id()
        self.connections[conn_id] = websocket_io
        await self.trigger_callbacks(WebsocketConnectEvent, websocket_io)
        if websocket_io.closed:
            return websocket_io.websocket
        with contextlib.suppress(ConnectionClosed):
            async for message in websocket_io.packets():
                await self.trigger_callbacks(WebsocketReceivedEvent, websocket_io, message)
        await self.trigger_callbacks(WebsocketCloseEvent, websocket_io)
        await websocket_io.close()
        return websocket_io.websocket

    async def trigger_callbacks(self, event, *args, **kwargs):
        callbacks = [i.get_callbacks(event) for i in self.transports if i.has_callback(event)]
        if callbacks:
            callbacks = reduce(lambda a, b: a + b, callbacks)
            await wait_fut([i(*args, **kwargs) for i in callbacks])

    def io(self, id: Optional[str] = None):
        if id is None:
            raise ValueError("id is required")

        return self.connections.get(id)

    def use(self, transport: Transport):
        self.transports.append(transport)
        for signature, handler in transport.iter_handlers():
            if isinstance(signature, HttpEndpoint):
                for method in signature.methods:
                    self.wsgi.router.add_route(method, signature.path, partial(self.handle_http_request, handler))

        for signature in transport.declares:
            if isinstance(signature, WebsocketEndpoint):
                self.wsgi.router.add_route("GET", signature.path, self.handle_websocket_request)


class AiohttpServerService(Service):
    id = "http.universal_server"
    wsgi_handler: web.Application
    supported_interface_types = {AiohttpRouter}

    def __init__(
        self, host: str = "127.0.0.1", port: int = 8000, wsgi_handler: Optional[web.Application] = None
    ) -> None:
        self.wsgi_handler = wsgi_handler or web.Application()
        self.wsgi_handler.router.freeze = lambda: None  # monkey patch
        self.routers: List[AiohttpRouter] = []
        self.host = host
        self.port = port
        super().__init__()

    def get_interface(self, interface_type):
        if interface_type is AiohttpRouter:
            router = AiohttpRouter(self.wsgi_handler)
            self.routers.append(router)
            return router

    @property
    def stages(self):
        return {"preparing", "blocking", "cleanup"}

    @property
    def required(self):
        return set()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            logger.info(f"starting server on {self.host}:{self.port}")
            runner = web.AppRunner(self.wsgi_handler)
            await runner.setup()
            site = web.TCPSite(runner, self.host, self.port)
        async with self.stage("blocking"):
            await site.start()
        async with self.stage("cleanup"):
            await self.wsgi_handler.shutdown()
            await self.wsgi_handler.cleanup()
