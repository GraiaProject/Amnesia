import asyncio

from aiohttp import ClientSession, ClientWebSocketResponse
from launart import Launart
from launart.component import Launchable
from launart.utilles import wait_fut
from loguru import logger
from richuru import install

from graia.amnesia.builtins.aiohttp import (
    AiohttpClientInterface,
    AiohttpRouter,
    AiohttpServerService,
    AiohttpService,
)
from graia.amnesia.builtins.starlette import StarletteRouter, StarletteService
from graia.amnesia.builtins.uvicorn import UvicornService
from graia.amnesia.json import TJson
from graia.amnesia.transport import Transport
from graia.amnesia.transport.common.http import HttpEndpoint
from graia.amnesia.transport.common.http.extra import HttpRequest, HttpResponse
from graia.amnesia.transport.common.http.io import (
    AbstactClientRequestIO,
    AbstractServerRequestIO,
)
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
mgr = Launart()
mgr.add_service(AiohttpService())
mgr.add_service(StarletteService())
mgr.add_service(UvicornService(port=21447))
# install()

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
        logger.success(f"server <- {data}")
        await io.send(f"received!{data!r}")
        # await io.close()

    @cbr.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("server: closed!")

    @cbr.handle(HttpEndpoint("/test", ["GET"]))
    async def test(self, req: AbstractServerRequestIO):
        logger.success(req)
        return {"code": 200, "msg": "ok"}


cbx = TransportRegistrar()


@cbx.apply
class TestWsClient(Transport):
    @cbx.handle(WebsocketReconnect)
    async def recon(self, stat: ConnectionStatus):
        await asyncio.sleep(1)
        logger.warning("reconnecting...")
        return True

    @cbx.on(WebsocketConnectEvent)
    async def connected(self, io: AbstractWebsocketIO):
        logger.info(await io.extra(HttpResponse))
        logger.success("client: connected!")
        await io.send(b"hello!")

    @cbx.on(WebsocketReceivedEvent)
    @data_type(str)
    async def received(self, io: AbstractWebsocketIO, data: str):
        logger.success(f"client <- {data}")
        await asyncio.sleep(1)
        await io.send(b"hello!")

    @cbx.on(WebsocketCloseEvent)
    async def closed(self, io: AbstractWebsocketIO):
        logger.success("client: closed!")


class Serve(Launchable):
    id = "serve"

    @property
    def required(self):
        return set()

    @property
    def stages(self):
        return set()

    async def launch(self, mgr: Launart):
        i = mgr.get_interface(StarletteRouter)
        t = TestWebsocketServer()
        i.use(t)


class Conn(Launchable):
    id = "conn"

    @property
    def required(self):
        return {"http.universal_client"}

    @property
    def stages(self):
        return {"blocking"}

    async def launch(self, mgr: Launart):
        async with self.stage("blocking"):
            logger.info("connecting...", style="red")
            ai = mgr.get_interface(AiohttpClientInterface)
            rider = ai.websocket("http://localhost:21447/ws_test")
            await asyncio.wait(
                [rider.use(TestWsClient()), mgr.status.wait_for_sigexit()], return_when=asyncio.FIRST_COMPLETED
            )


mgr.add_launchable(Serve())
mgr.add_launchable(Conn())

mgr.launch_blocking(loop=loop)
