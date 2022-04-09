import asyncio

from aiohttp import ClientSession
from loguru import logger

from graia.amnesia.builtins.aiohttp import AiohttpClientInterface, AiohttpService
from graia.amnesia.builtins.starlette import (
    StarletteRouter,
    StarletteServer,
    StarletteService,
)
from graia.amnesia.builtins.uvicorn import UvicornService
from graia.amnesia.json import TJson
from graia.amnesia.launch.manager import LaunchManager
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpRequest
from graia.amnesia.transport.common.websocket import (
    AbstractWebsocketIO,
    WebsocketCloseEvent,
    WebsocketConnectEvent,
    WebsocketEndpoint,
    WebsocketReceivedEvent,
)
from graia.amnesia.transport.common.websocket.shortcut import data_type, json_require
from graia.amnesia.transport.utilles import TransportRegistrar

loop = asyncio.get_event_loop()
mgr = LaunchManager()
mgr.add_service(AiohttpService(ClientSession(loop=loop)))
mgr.add_service(StarletteService())
mgr.add_service(UvicornService("127.0.0.1", 8000))

cbr = TransportRegistrar()


@cbr.apply
class TestWebsocketServer(Transport):
    cbr.declare(WebsocketEndpoint("/ws_test"))

    @cbr.on(WebsocketConnectEvent)
    async def connected(self, io: AbstractWebsocketIO):
        print("?")
        req = await io.extra(HttpRequest)
        logger.info(req)
        if req.url.path == "/ws_test":
            logger.info("connected")
            await io.accept()
            # await io.wait_for_ready()
            await io.send("hello")
        else:
            await io.close()
        logger.success("websocket connected!")

    @cbr.on(WebsocketReceivedEvent)
    @data_type(bytes)
    async def received_b(self, io: AbstractWebsocketIO, data: bytes):
        logger.success(f"websocket received: {data}")
        await io.send(f"received bytes!{data!r}")
        # await io.close()

    @cbr.on(WebsocketReceivedEvent)
    @data_type(str)
    @json_require
    async def received(self, io: AbstractWebsocketIO, data: TJson):
        logger.success(f"websocket received: {data}")
        await io.send(f"received!{data!r}")
        # await io.close()

    @cbr.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("websocket closed!")


cbx = TransportRegistrar()


@cbx.apply
class TestWsClient(Transport):
    @cbx.on(WebsocketConnectEvent)
    async def connected(self, io: AbstractWebsocketIO):
        logger.info(io.extra(HttpRequest))
        if io.extra(HttpRequest) == "/test":
            pass
        logger.success("websocket connected!")
        await io.send(b"hello!")

    @cbx.on(WebsocketReceivedEvent)
    async def received(self, io: AbstractWebsocketIO, data: bytes):
        logger.success(f"websocket received: {data}")

    @cbx.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("websocket closed!")


async def main(_):
    i = mgr.get_interface(StarletteRouter)
    t = TestWebsocketServer()
    logger.info(list(t.iter_handlers()))
    i.use(t)


mgr.new_launch_component("test", mainline=main)
mgr.launch_blocking(loop=loop)
