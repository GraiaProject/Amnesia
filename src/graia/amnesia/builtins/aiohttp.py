import asyncio
import weakref
from functools import partial, reduce
from typing import Any, Generic, Optional, Type, TypeVar, Union, cast, overload

from aiohttp import ClientResponse, ClientSession, ClientWebSocketResponse, WSMsgType

from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.service import Service
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import (
    AbstactClientRequestIO,
    AbstractWebsocketIO,
    HttpResponse,
    websocket,
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
        if signature is websocket.close:
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


T = TypeVar("T", ClientResponse, ClientWebSocketResponse)


class ClientConnectionRider(TransportRider[str, Any], Generic[T]):
    def __init__(self, response: T):
        self.transports = []
        self.response = response
        self.connections = {}
        self.connections["default"] = response
        self.autoreceive = False
        self.task = None

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

    async def connection_manage(self: "ClientConnectionRider[ClientWebSocketResponse]"):
        io = ClientWebsocketIO(self.response)
        await self.trigger_callbacks(websocket.event.connect, io)
        try:
            async for data in io.packets():
                await self.trigger_callbacks(websocket.event.receive, io, data)
        finally:
            await self.trigger_callbacks(websocket.event.close, io)
            if not io.closed:
                await io.close()

    def use(self, transport: Transport):
        # 因为我不能直接给你就全部接管 receive data, 所以.
        # 不过我可以提供选择.
        # TODO: 中间件, 自动 receive 并触发 websocket.data_received 的 Transport Callbacks.
        if not isinstance(self.response, ClientWebSocketResponse):
            raise TypeError("this response is not a packet io.")
        self.autoreceive = True
        self.transports.append(transport)
        if not self.task:
            self.task = asyncio.create_task(self.connection_manage())  # type: ignore
        return self.task


class AiohttpClientInterface(ExportInterface["AiohttpService"]):
    service: "AiohttpService"

    def __init__(self, service: "AiohttpService") -> None:
        self.service = service

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        timeout: Optional[float] = None,
    ):
        response = await self.service.session.request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
        ).__aenter__()
        return ClientConnectionRider(response)

    async def websocket(self, url: str, **kwargs):
        connection = await self.service.session.ws_connect(url, **kwargs).__aenter__()
        return ClientConnectionRider(connection)


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