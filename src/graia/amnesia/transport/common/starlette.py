import asyncio
import pathlib
from functools import partial, reduce
from typing import Optional, Union
from weakref import WeakValueDictionary

import yarl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.websockets import WebSocket, WebSocketState

from graia.amnesia.builtins.common import ASGIHandlerProvider
from graia.amnesia.interface import ExportInterface
from graia.amnesia.launch import LaunchComponent
from graia.amnesia.service import Service
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import (
    AbstractServerRequestIO,
    AbstractWebsocketIO,
    HttpRequest,
    http,
    websocket,
)
from graia.amnesia.transport.exceptions import ConnectionClosed
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.utilles import random_id

# 这里为简化版, 完整版是在 avilla.io 那边


class StarletteServer(ASGIHandlerProvider):
    starlette: Starlette
    service: "StarletteService"

    def __init__(self, service: "StarletteService", starlette: Starlette):
        self.service = service
        self.starlette = starlette

        super().__init__()

    def get_asgi_handler(self):
        return self.starlette


class StarletteRequestIO(AbstractServerRequestIO):
    request: Request

    def __init__(self, request: Request) -> None:
        self.request = request

    async def read(self) -> bytes:
        return await self.request.body()

    async def extra(self, signature):
        if signature is HttpRequest:
            url = self.request.url
            return HttpRequest(
                dict(self.request.headers),
                self.request.cookies,
                dict(self.request.query_params),
                yarl.URL.build(
                    scheme=url.scheme,
                    user=url.username,
                    password=url.password,
                    host=url.hostname or "",
                    port=url.port,
                    path=url.path,
                    query=url.query,
                    fragment=url.fragment,
                ),
                self.request.url.hostname or self.request.headers.get("Host", ""),
                self.request.method,
                self.request.client.host if self.request.client else ".0.0.0",
                self.request.client.port if self.request.client else 0,
            )

    async def headers(self):
        return dict(self.request.headers)

    async def cookies(self):
        return self.request.cookies


class StarletteWebsocketIO(AbstractWebsocketIO):
    websocket: WebSocket

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket

    async def receive(self) -> Union[str, bytes]:
        received = await self.websocket.receive()
        if "text" in received:
            return received["text"]
        elif "bytes" in received:
            return received["bytes"]
        else:
            if self.websocket.client_state == WebSocketState.DISCONNECTED:
                raise ConnectionClosed("Connection closed")
            raise TypeError("Unknown type of received message" f"{received}")

    async def send(self, data: Union[bytes, str]):
        if isinstance(data, str):
            await self.websocket.send_text(data)
        elif isinstance(data, bytes):
            await self.websocket.send_bytes(data)
        else:
            raise TypeError("Unknown type of data to send")

    async def extra(self, signature):
        if signature is HttpRequest:
            url = self.websocket.url
            return HttpRequest(
                dict(self.websocket.headers),
                self.websocket.cookies,
                dict(self.websocket.query_params),
                yarl.URL.build(
                    scheme=url.scheme,
                    user=url.username,
                    password=url.password,
                    host=url.hostname or "",
                    port=url.port,
                    path=url.path,
                    query=url.query,
                    fragment=url.fragment,
                ),
                self.websocket.url.hostname or self.websocket.headers.get("Host", ""),
                "WS",
                self.websocket.client.host if self.websocket.client else "0.0.0.0",
                self.websocket.client.port if self.websocket.client else 0,
            )
        elif signature is websocket.accept:
            await self.websocket.accept()
        elif signature is websocket.close:
            await self.websocket.close()

    async def headers(self):
        return dict(self.websocket.headers)

    async def cookies(self):
        return self.websocket.cookies

    async def close(self):
        await self.websocket.close()

    @property
    def closed(self):
        return self.websocket.client_state == WebSocketState.DISCONNECTED


class StarletteRouter(ExportInterface, TransportRider[str, object]):  # TODO: generic type change
    def __init__(self, starlette: Starlette):
        self.starlette = starlette
        self.connections = WeakValueDictionary()  # type: ignore
        self.transports = []

    async def http_request_handler(self, handler, request: Request):
        io = StarletteRequestIO(request)
        conn_id = random_id()
        self.connections[conn_id] = io
        try:
            response = await handler(io)
        finally:
            del self.connections[conn_id]

        if not isinstance(response, tuple):
            response_body = response
            response_desc = {}
        else:
            response_body = response[0]
            response_desc = reduce(lambda x, y: dict(x, **y), response[1:], {})

        if isinstance(response_body, (str, bytes)):
            starlette_resp = PlainTextResponse(
                response_body, status_code=response_desc.get("status", 200), headers=response_desc.get("headers")
            )
        elif isinstance(response_body, (dict, list)):
            starlette_resp = JSONResponse(
                response_body, status_code=response_desc.get("status", 200), headers=response_desc.get("headers")
            )
        elif isinstance(response_body, pathlib.Path):
            starlette_resp = FileResponse(
                response_body, status_code=response_desc.get("status", 200), headers=response_desc.get("headers")
            )
        elif isinstance(response_body, Response):
            starlette_resp = response_body
        else:
            raise ValueError(f"unsupported response type {type(response_body)}")

        if "cookies" in response_desc:
            expire = response_desc.get("cookie_expires")
            for key, value in response_desc["cookies"].items():
                starlette_resp.set_cookie(key, value, expire)

        return starlette_resp

    async def trigger_callbacks(self, event, *args, **kwargs):
        callbacks = [i.get_callbacks(event) for i in self.transports if i.has_callback(event)]
        if callbacks:
            callbacks = reduce(lambda a, b: a + b, callbacks)
            await asyncio.wait([i(*args, **kwargs) for i in callbacks])

    async def websocket_handler(self, ws: WebSocket):
        io = StarletteWebsocketIO(ws)
        conn_id = random_id()
        self.connections[conn_id] = io
        await self.trigger_callbacks(websocket.event.connect, io)
        async for message in io.packets():
            await self.trigger_callbacks(websocket.event.receive, io, message)
        await self.trigger_callbacks(websocket.event.close, io)

    def use(self, transport: Transport):
        for signature, handler in transport.iter_handlers():
            if isinstance(signature, http.endpoint):
                self.starlette.add_route(
                    signature.path, partial(self.http_request_handler, handler), methods=signature.methods
                )
            elif isinstance(signature, websocket.endpoint):
                self.starlette.add_websocket_route(signature.path, self.websocket_handler)


class StarletteService(Service):
    supported_interface_types = {ASGIHandlerProvider}

    starlette: Starlette

    def __init__(self, starlette: Optional[Starlette] = None) -> None:
        self.starlette = starlette or Starlette()
        super().__init__()

    def get_interface(self, interface_type):
        if issubclass(interface_type, (ASGIHandlerProvider)):
            return StarletteServer(self, self.starlette)
        raise ValueError(f"unsupported interface type {interface_type}")

    @property
    def launch_component(self) -> LaunchComponent:
        return LaunchComponent("http.universal_server", set())
