import asyncio

from aiohttp import ClientSession, ClientWebSocketResponse
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
from graia.amnesia.log import install
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http.extra import HttpRequest, HttpResponse
from graia.amnesia.transport.common.status import ConnectionStatus
from graia.amnesia.transport.common.websocket import (
    AbstractWebsocketIO,
    WebsocketCloseEvent,
    WebsocketConnectEvent,
    WebsocketEndpoint,
    WebsocketReceivedEvent,
)
from graia.amnesia.transport.common.websocket.event import WebsocketReconnect
from graia.amnesia.transport.common.websocket.shortcut import data_type, json_require
from graia.amnesia.transport.rider import TransportRider
from graia.amnesia.transport.utilles import TransportRegistrar

loop = asyncio.get_event_loop()
mgr = LaunchManager()
mgr.add_service(AiohttpService())
mgr.add_service(StarletteService())
mgr.add_service(UvicornService("127.0.0.1", 8000))
install(mgr.rich_console)
cbr = TransportRegistrar()


@cbr.apply
class TestWebsocketServer(Transport):
    c = 0
    cbr.declare(WebsocketEndpoint("/ws_test"))

    @cbr.on(WebsocketConnectEvent)
    async def connected(self, io: AbstractWebsocketIO):
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
        await io.send(f"reply - {data!r}")
        self.c += 1
        if self.c >= 2:
            await io.close()

    @cbr.on(WebsocketReceivedEvent)
    @data_type(str)
    async def received(self, io: AbstractWebsocketIO, data: str):
        logger.success(f"server received: {data}")
        await io.send(f"received!{data!r}")
        # await io.close()

    @cbr.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("websocket closed!")


cbx = TransportRegistrar()


@cbx.apply
class TestWsClient(Transport):
    @cbx.handle(WebsocketReconnect)
    async def recon(self, rider: ConnectionStatus):
        await asyncio.sleep(1)
        logger.warning("reconnecting...")
        return rider.succeed

    @cbx.on(WebsocketConnectEvent)
    async def connected(self, io: AbstractWebsocketIO):
        logger.info(await io.extra(HttpResponse))
        logger.success("websocket connected!")
        await io.send(b"hello!")

    @cbx.on(WebsocketReceivedEvent)
    @data_type(str)
    async def received(self, io: AbstractWebsocketIO, data: str):
        logger.success(f"client received: {data}")
        await asyncio.sleep(1)
        await io.send(b"hello!")

    @cbx.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("websocket closed!")


async def serve(mgr: LaunchManager):
    i = mgr.get_interface(StarletteRouter)
    t = TestWebsocketServer()
    logger.info(list(t.iter_handlers()))
    i.use(t)


async def conn(mgr: LaunchManager):
    logger.info("connecting...", style="red")
    ai = mgr.get_interface(AiohttpClientInterface)
    req_rider = await ai.request("GET", "https://httpbin.org/get")  # a simple httpbin get
    mgr.rich_console.print(await req_rider.io().response.json())
    rider = ai.websocket("http://localhost:8000/ws_test")
    await rider.use(TestWsClient())


mgr.new_launch_component("serve", mainline=serve)
mgr.new_launch_component("conn", {"serve"}, mainline=conn)

mgr.launch_blocking(loop=loop)
